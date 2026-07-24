// composables/useJournalEngine.ts
// Движок исполнения журнала с поддержкой сохранения прогресса

import { computed, ref, watch } from 'vue'
import jsonLogic from 'json-logic-js'
import type {
  AnswerRow,
  JournalAnswers,
  JournalConditionData,
  JournalEntry,
  JournalField,
  JournalLoopData,
  JournalNode,
  JournalSchema,
  JournalStepData,
  Screen,
  TableBlock
} from '@/modules/workflows/types/journal'
import { ensureV2, screenFields, toScreen } from '@/modules/workflows/engine/convert'
import {
  applyComputedFields,
  fieldsSatisfied,
  isFieldSatisfied
} from '@/modules/workflows/engine/fields'

function findNode(schema: JournalSchema, id: string): JournalNode {
  const node = schema.nodes.find((n) => n.id === id)
  if (!node) throw new Error(`Journal node "${id}" not found in schema "${schema.id}"`)
  return node
}

function outgoingEdges(schema: JournalSchema, nodeId: string) {
  return schema.edges.filter((e) => e.source === nodeId)
}

function advance(schema: JournalSchema, fromNodeId: string, answers: JournalAnswers): JournalNode {
  let current = findNode(schema, fromNodeId)

  for (let i = 0; i < schema.nodes.length + 1; i++) {
    let next: JournalNode

    if (current.type === 'condition') {
      const { rule } = current.data as JournalConditionData
      const result = Boolean(jsonLogic.apply(rule as never, answers))
      const handle = result ? 'true' : 'false'
      const edge = outgoingEdges(schema, current.id).find((e) => e.sourceHandle === handle)
      if (!edge) throw new Error(`Condition node "${current.id}" has no "${handle}" branch`)
      next = findNode(schema, edge.target)
    } else {
      const edges = outgoingEdges(schema, current.id)
      if (!edges.length) throw new Error(`Node "${current.id}" (${current.type}) has no outgoing edge`)
      next = findNode(schema, edges[0].target)
    }

    current = next
    if (current.type === 'step' || current.type === 'loop' || current.type === 'end') {
      return current
    }
  }

  throw new Error(`Could not resolve next step from "${fromNodeId}" — possible cycle in schema "${schema.id}"`)
}

export function useJournalEngine(
  schema: JournalSchema,
  options?: {
    // Pre-loaded record to seed from. setup() cannot await, so the caller
    // fetches the run (via the async API) and hands the DTO in here.
    initialEntry?: JournalEntry
    onSave?: (
      answers: JournalAnswers,
      history: string[],
      currentNodeId: string,
      loops: Record<string, JournalAnswers[]>,
    ) => void
  },
) {
  // Нормализуем схему к v2 один раз: у каждого step/loop-узла появляется screen,
  // граф/условия/рёбра не меняются (§7). Дальше движок работает поверх `s`.
  const s = ensureV2(schema)

  const startNode = s.nodes.find((n) => n.type === 'start')
  if (!startNode) throw new Error(`Schema "${s.id}" has no start node`)

  // Восстановление состояния из переданной записи
  const savedEntry = options?.initialEntry

  const answers = ref<JournalAnswers>(savedEntry?.answers ?? {})
  const history = ref<string[]>(savedEntry?.history ?? [])
  // Накопленные итерации циклических нод: loopNodeId -> массив снимков ответов
  const loops = ref<Record<string, JournalAnswers[]>>(savedEntry?.loops ?? {})

  // Все computed-поля схемы (top-level, по всем step/loop-экранам). Пересчёт
  // держит их значения в answers — доступны условиям, действиям и следующим
  // шагам (schema-doc §4). Циклические зависимости не разрешаются (MVP).
  const computedFields: JournalField[] = s.nodes.flatMap((n) => {
    if (n.type !== 'step' && n.type !== 'loop') return []
    return screenFields(toScreen(n.data as JournalStepData | JournalLoopData)).filter(
      (f) => f.type === 'computed',
    )
  })

  // Пересчёт computed при любом изменении answers. Запись идёт только при
  // фактическом изменении значения, поэтому watcher сходится за один тик.
  if (computedFields.length) {
    watch(
      answers,
      () => {
        applyComputedFields(computedFields, answers.value)
      },
      { deep: true, immediate: true },
    )
  }

  // Определяем стартовую ноду
  const initialNodeId = savedEntry?.currentNodeId ?? startNode.id
  const currentStep = ref<JournalNode>(
    initialNodeId === 'start'
      ? advance(s, startNode.id, answers.value)
      : findNode(s, initialNodeId),
  )

  const isFinished = computed(() => currentStep.value.type === 'end')

  // Экран текущего шага (грид v2). Для не-step/loop нод — пустой экран.
  const currentScreen = computed<Screen>(() => {
    const t = currentStep.value.type
    if (t !== 'step' && t !== 'loop') return { rows: [] }
    return toScreen(currentStep.value.data as JournalStepData | JournalLoopData)
  })

  // Плоские поля текущего шага (step или loop) — из экрана. Используются для
  // required-валидации и сводки итераций цикла.
  const currentFields = computed<JournalField[]>(() => {
    const t = currentStep.value.type
    if (t !== 'step' && t !== 'loop') return []
    return screenFields(currentScreen.value)
  })

  // Данные циклической ноды (или null, если текущий шаг не цикл)
  const currentLoop = computed<JournalLoopData | null>(() =>
    currentStep.value.type === 'loop' ? (currentStep.value.data as JournalLoopData) : null,
  )

  // Уже добавленные итерации текущей циклической ноды
  const loopItems = computed<JournalAnswers[]>(() =>
    currentLoop.value ? loops.value[currentStep.value.id] ?? [] : [],
  )

  // Table-блоки текущего экрана (для валидации минимального числа строк и
  // обязательных колонок при переходе «Далее»).
  const currentTables = computed<TableBlock[]>(() => {
    const out: TableBlock[] = []
    for (const row of currentScreen.value.rows) {
      for (const block of row.blocks) {
        if (block.kind === 'table') out.push(block.table)
      }
    }
    return out
  })

  // Базовая валидация таблиц: минимум строк + обязательные/валидные колонки в
  // каждой строке. Контекст для visibleWhen/валидации колонки — answers,
  // дополненные значениями самой строки (колонки ссылаются друг на друга).
  function tablesSatisfied(tables: TableBlock[]): boolean {
    return tables.every((table) => {
      const rows = (answers.value[table.fieldId] as AnswerRow[] | undefined) ?? []
      if (rows.length < (table.minRows ?? 0)) return false
      return rows.every((row) => {
        const context = { ...answers.value, ...row }
        return table.columns.every((col) => isFieldSatisfied(col, context))
      })
    })
  }

  // Заполнены ли обязательные поля текущей (в процессе) итерации цикла —
  // нужно, чтобы разрешить кнопку «Добавить». Скрытые поля не требуются.
  const canAddLoopItem = computed(() => fieldsSatisfied(currentFields.value, answers.value))

  const canGoNext = computed(() => {
    // Из циклической ноды выйти можно всегда — число итераций на усмотрение
    // пользователя (в т.ч. ноль).
    if (currentLoop.value) return true
    return (
      fieldsSatisfied(currentFields.value, answers.value)
      && tablesSatisfied(currentTables.value)
    )
  })

  const progress = computed(() => {
    if (isFinished.value) return 100
    const totalSteps = s.nodes.filter((n) => n.type === 'step').length
    if (!totalSteps) return 0
    return Math.min(100, Math.round((history.value.length / totalSteps) * 100))
  })

  function persist() {
    if (options?.onSave) {
      options.onSave(answers.value, history.value, currentStep.value.id, loops.value)
    }
  }

  // Очистить значения полей текущей итерации цикла из плоских answers
  function clearLoopFields() {
    for (const f of currentFields.value) delete answers.value[f.id]
  }

  // Зафиксировать одну итерацию цикла (доп. тест) и подготовить форму к
  // следующей. Число итераций пользователь выбирает сам.
  function addLoopItem() {
    if (!currentLoop.value || !canAddLoopItem.value) return
    const nodeId = currentStep.value.id
    const snapshot: JournalAnswers = {}
    for (const f of currentFields.value) {
      const v = answers.value[f.id]
      if (v !== undefined) snapshot[f.id] = v
    }
    const list = loops.value[nodeId] ? [...loops.value[nodeId]] : []
    list.push(snapshot)
    loops.value = { ...loops.value, [nodeId]: list }
    clearLoopFields()
    persist()
  }

  function removeLoopItem(index: number) {
    if (!currentLoop.value) return
    const nodeId = currentStep.value.id
    const list = [...(loops.value[nodeId] ?? [])]
    list.splice(index, 1)
    loops.value = { ...loops.value, [nodeId]: list }
    persist()
  }

  function goNext() {
    if (!canGoNext.value || isFinished.value) return
    // Выходя из цикла, отбрасываем незафиксированную «черновую» итерацию
    if (currentLoop.value) clearLoopFields()
    history.value.push(currentStep.value.id)
    currentStep.value = advance(s, currentStep.value.id, answers.value)
    persist()
  }

  function goBack() {
    const prevId = history.value.pop()
    if (!prevId) return
    currentStep.value = findNode(s, prevId)
    persist()
  }

  function reset() {
    answers.value = {}
    history.value = []
    loops.value = {}
    currentStep.value = advance(s, startNode!.id, answers.value)
    persist()
  }

  // Загрузить сохранённое состояние конкретной записи (продолжение
  // заполнения — в т.ч. другим сотрудником). НЕ перезаписываем прогресс.
  // Запись предзагружается вызывающим (async API) и передаётся сюда как DTO.
  function load(e: JournalEntry | null | undefined) {
    if (!e) {
      reset()
      return
    }
    answers.value = e.answers ?? {}
    history.value = e.history ?? []
    loops.value = e.loops ?? {}
    const nodeId = e.currentNodeId ?? startNode!.id
    currentStep.value =
      nodeId === 'start'
        ? advance(s, startNode!.id, answers.value)
        : findNode(s, nodeId)
  }

  return {
    answers,
    currentStep,
    currentScreen,
    currentFields,
    currentLoop,
    loopItems,
    canAddLoopItem,
    addLoopItem,
    removeLoopItem,
    canGoNext,
    isFinished,
    history,
    loops,
    progress,
    goNext,
    goBack,
    reset,
    load,
  }
}