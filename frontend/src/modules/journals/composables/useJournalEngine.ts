// composables/useJournalEngine.ts
// Движок исполнения журнала с поддержкой сохранения прогресса

import { computed, ref } from 'vue'
import jsonLogic from 'json-logic-js'
import type {
  JournalAnswers,
  JournalConditionData,
  JournalField,
  JournalLoopData,
  JournalNode,
  JournalSchema,
  JournalStepData
} from '@/modules/journals/types/journal'
import { getEntry } from './useJournalStorage'

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
    entryId?: string
    onSave?: (
      answers: JournalAnswers,
      history: string[],
      currentNodeId: string,
      loops: Record<string, JournalAnswers[]>,
    ) => void
  },
) {
  const startNode = schema.nodes.find((n) => n.type === 'start')
  if (!startNode) throw new Error(`Schema "${schema.id}" has no start node`)

  // Восстановление состояния из entry
  const savedEntry = options?.entryId ? getEntry(options.entryId) : undefined

  const answers = ref<JournalAnswers>(savedEntry?.answers ?? {})
  const history = ref<string[]>(savedEntry?.history ?? [])
  // Накопленные итерации циклических нод: loopNodeId -> массив снимков ответов
  const loops = ref<Record<string, JournalAnswers[]>>(savedEntry?.loops ?? {})

  // Определяем стартовую ноду
  const initialNodeId = savedEntry?.currentNodeId ?? startNode.id
  const currentStep = ref<JournalNode>(
    initialNodeId === 'start'
      ? advance(schema, startNode.id, answers.value)
      : findNode(schema, initialNodeId),
  )

  const isFinished = computed(() => currentStep.value.type === 'end')

  // Поля текущего шага — и обычного (step), и циклического (loop)
  const currentFields = computed<JournalField[]>(() => {
    const t = currentStep.value.type
    if (t !== 'step' && t !== 'loop') return []
    return (currentStep.value.data as JournalStepData | JournalLoopData).fields
  })

  // Данные циклической ноды (или null, если текущий шаг не цикл)
  const currentLoop = computed<JournalLoopData | null>(() =>
    currentStep.value.type === 'loop' ? (currentStep.value.data as JournalLoopData) : null,
  )

  // Уже добавленные итерации текущей циклической ноды
  const loopItems = computed<JournalAnswers[]>(() =>
    currentLoop.value ? loops.value[currentStep.value.id] ?? [] : [],
  )

  // Заполнены ли обязательные поля текущей (в процессе) итерации цикла —
  // нужно, чтобы разрешить кнопку «Добавить»
  const canAddLoopItem = computed(() =>
    currentFields.value
      .filter((f) => f.required)
      .every((f) => {
        const v = answers.value[f.id]
        return v !== undefined && v !== null && v !== ''
      }),
  )

  const canGoNext = computed(() => {
    // Из циклической ноды выйти можно всегда — число итераций на усмотрение
    // пользователя (в т.ч. ноль).
    if (currentLoop.value) return true
    return currentFields.value
      .filter((f) => f.required)
      .every((f) => {
        const v = answers.value[f.id]
        return v !== undefined && v !== null && v !== ''
      })
  })

  const progress = computed(() => {
    if (isFinished.value) return 100
    const totalSteps = schema.nodes.filter((n) => n.type === 'step').length
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
    currentStep.value = advance(schema, currentStep.value.id, answers.value)
    persist()
  }

  function goBack() {
    const prevId = history.value.pop()
    if (!prevId) return
    currentStep.value = findNode(schema, prevId)
    persist()
  }

  function reset() {
    answers.value = {}
    history.value = []
    loops.value = {}
    currentStep.value = advance(schema, startNode!.id, answers.value)
    persist()
  }

  // Загрузить сохранённое состояние конкретной записи (продолжение
  // заполнения — в т.ч. другим сотрудником). НЕ перезаписываем прогресс.
  function load(entryId: string) {
    const e = getEntry(entryId)
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
        ? advance(schema, startNode!.id, answers.value)
        : findNode(schema, nodeId)
  }

  return {
    answers,
    currentStep,
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