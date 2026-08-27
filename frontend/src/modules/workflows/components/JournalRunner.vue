<script setup lang="ts">
// components/JournalRunner.vue
// UI для заполнения журнала с сохранением прогресса и управлением записями

import { computed, onMounted, ref, watch } from 'vue';
import type { TimelineItem } from '@nuxt/ui';
import { useToast } from '@nuxt/ui/composables';
import ConfirmDialog from '@/shared/ui/ConfirmDialog.vue';
import WorkflowScreenRenderer from '@/modules/workflows/components/WorkflowScreenRenderer.vue';
import { useJournalUser } from '@/modules/workflows/composables/useJournalUser';
import { useJournalEngine } from '@/modules/workflows/composables/useJournalEngine';
import { addComment, createEntry, deleteEntry, executeStep, getEntriesForSchema, getEntry, saveEntryProgress } from '@/modules/workflows/api/workflows.api';
import { StepAttemptTracker, resolveActions } from '@/modules/workflows/engine/actions';
import type { ApiClientError } from '@/shared/api/client.api';
import type { JournalActivityType, JournalEntry, JournalNode, JournalSchema, JournalStepData } from '@/modules/workflows/types/journal';

const props = defineProps<{
  schema: JournalSchema
  templateId: string
  // Привязка записей к внешней сущности (например, id исследования): список и
  // создание записей ограничиваются этой областью.
  scope?: string
  // Предзаполнение названия новой записи (например, номер исследования).
  defaultTitle?: string
}>()

const emit = defineEmits<{
  'entry-created': [string]
  'entry-completed': [string]
}>()

const { current: currentUser, authorName } = useJournalUser()
const toast = useToast()

// Попытки execute-step по (run, node): прозрачный ретрай шлёт тот же attempt.
const attempts = new StepAttemptTracker()
// Последняя причина отказа доменного действия (например, запрет перехода 409),
// показывается инлайном на шаге, чтобы шаг не «проваливался молча».
const actionError = ref<string | null>(null)

// Управление записями
const showNewEntryModal = ref(false)
const newEntryTitle = ref('')
const selectedEntryId = ref<string | null>(null)
const showEntriesList = ref(false)
const newComment = ref('')

// Список записей (перечитывается из API после каждого изменения)
const entries = ref<JournalEntry[]>([])
async function loadEntries() {
  entries.value = await getEntriesForSchema(props.templateId, props.schema.version, props.scope)
}
onMounted(loadEntries)

// Актуальный снимок открытой записи (мета/комментарии/история) —
// перечитываем из API после каждого изменения
const activeEntry = ref<JournalEntry | null>(null)
async function refreshActiveEntry() {
  activeEntry.value = selectedEntryId.value ? (await getEntry(selectedEntryId.value)) ?? null : null
  await loadEntries()
}
const currentEntry = computed(() => activeEntry.value ?? undefined)

// Движок. Прогресс сохраняется через API (fire-and-forget), затем снимок
// записи перечитывается для боковой панели/истории.
const engine = useJournalEngine(props.schema, {
  onSave: (answers, history, currentNodeId, loops) => {
    if (selectedEntryId.value) {
      void saveEntryProgress(selectedEntryId.value, answers, history, currentNodeId, loops)
        .then(() => refreshActiveEntry())
    }
  },
})

// Комментарии к текущему шагу
const currentNodeId = computed(() => engine.currentStep.value.id)
// Причина отказа действия относится к конкретному шагу — сбрасываем при переходе.
watch(currentNodeId, () => { actionError.value = null })
const currentNodeComments = computed(() =>
  (activeEntry.value?.comments ?? []).filter((c) => c.nodeId === currentNodeId.value),
)

async function submitComment() {
  const text = newComment.value.trim()
  if (!text || !selectedEntryId.value) return
  await addComment(selectedEntryId.value, currentNodeId.value, authorName(), text)
  newComment.value = ''
  await refreshActiveEntry()
}

// Выполнить доменные действия шага через backend execute-step (US-007). Возвращает
// true, если можно переходить дальше. Три исхода различимы в UI:
//   applied         — успех (тост success);
//   already_applied — тихий успех при ретрае (тост neutral), идём дальше;
//   409 / ошибка    — остаёмся на шаге, показываем причину (тост error + инлайн).
async function runStepActions(step: JournalNode): Promise<boolean> {
  const actions = (step.data as JournalStepData).actions ?? []
  if (!actions.length || !selectedEntryId.value) return true

  const runId = selectedEntryId.value
  const nodeId = step.id
  const resolved = resolveActions(actions, {
    answers: engine.answers.value,
    actorId: null,
    scopeId: props.scope,
  })
  const attempt = attempts.current(runId, nodeId)
  const call = () =>
    executeStep(runId, { nodeId, attempt, actions: resolved, author: authorName() })

  actionError.value = null
  try {
    let outcome
    try {
      outcome = await call()
    } catch (error) {
      // Сетевой сбой (нет HTTP-статуса) — один прозрачный ретрай тем же attempt.
      if (!(error as ApiClientError)?.status) {
        outcome = await call()
      } else {
        throw error
      }
    }
    toast.add(
      outcome.alreadyApplied
        ? { title: 'Действие уже было выполнено', color: 'neutral', icon: 'i-lucide-check' }
        : { title: 'Действие выполнено', color: 'success', icon: 'i-lucide-check' },
    )
    await refreshActiveEntry()
    return true
  } catch (error) {
    const apiError = error as ApiClientError
    const reason = apiError?.message || 'Не удалось выполнить действие шага'
    actionError.value = reason
    toast.add({
      title: apiError?.status === 409 ? 'Переход запрещён' : 'Ошибка действия',
      description: reason,
      color: 'error',
      icon: 'i-lucide-circle-alert',
    })
    return false
  }
}

// Обёртка «Далее»: доменные действия шага выполняются сервером ПЕРЕД переходом
// (при запрете перехода 409 остаёмся на шаге). Сохранение прогресса и
// авто-завершение на финише выполняются движком через onSave → saveEntryProgress.
async function onNext() {
  if (!engine.canGoNext.value || engine.isFinished.value) return
  const completed = engine.currentStep.value
  if (!(await runStepActions(completed))) return
  engine.goNext()
  if (selectedEntryId.value && engine.currentStep.value.id !== completed.id) {
    if (engine.isFinished.value) {
      emit('entry-completed', selectedEntryId.value)
    }
    await refreshActiveEntry()
  }
}

const stepData = computed(() => engine.currentStep.value.data as JournalStepData)

// Краткая сводка одной итерации цикла для списка добавленных
function loopItemSummary(item: Record<string, unknown>): string {
  const fields = engine.currentFields.value
  return fields
    .map((f) => {
      const v = item[f.id]
      if (v === undefined || v === null || v === '') return null
      if (f.type === 'boolean') return `${f.label}: ${v ? 'да' : 'нет'}`
      if (f.type === 'select') {
        const opt = f.options?.find((o) => o.value === v)
        return `${f.label}: ${opt?.label ?? v}`
      }
      return `${f.label}: ${v}`
    })
    .filter(Boolean)
    .join(' · ')
}

function formatDateTime(iso?: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const activityMeta: Record<JournalActivityType, { icon: string; color: string; verb: string }> = {
  created: { icon: 'i-lucide-file-plus', color: 'text-primary', verb: 'создал(а) запись' },
  step_completed: { icon: 'i-lucide-check', color: 'text-success', verb: 'заполнил(а) шаг' },
  comment_added: { icon: 'i-lucide-message-square', color: 'text-info', verb: 'оставил(а) комментарий к' },
  reopened: { icon: 'i-lucide-folder-open', color: 'text-warning', verb: 'открыл(а) запись' },
  completed: { icon: 'i-lucide-flag', color: 'text-success', verb: 'завершил(а) журнал' },
  reset: { icon: 'i-lucide-rotate-ccw', color: 'text-muted', verb: 'сбросил(а) запись' },
}

// История в обратном порядке (свежие сверху)
const activityLog = computed(() => [...(activeEntry.value?.activity ?? [])].reverse())

// Элементы UTimeline для истории записи.
const historyItems = computed<TimelineItem[]>(() =>
  activityLog.value.map((ev) => ({
    value: ev.id,
    icon: activityMeta[ev.type].icon,
    title: `${ev.author} ${activityMeta[ev.type].verb}${ev.label ? ` «${ev.label}»` : ''}`,
    date: formatDateTime(ev.at),
  })),
)

function entryStatusColor(status?: string): 'success' | 'warning' {
  return status === 'completed' ? 'success' : 'warning'
}
function entryStatusLabel(status?: string): string {
  return status === 'completed' ? 'Завершено' : 'Черновик'
}

function openNewEntryModal() {
  newEntryTitle.value = props.defaultTitle ?? ''
  showNewEntryModal.value = true
}

async function startNewEntry() {
  if (!newEntryTitle.value.trim()) return
  const entry = await createEntry(props.templateId, props.schema.version, newEntryTitle.value.trim(), props.scope)
  selectedEntryId.value = entry.id
  showNewEntryModal.value = false
  newEntryTitle.value = ''
  showEntriesList.value = false
  // Новая запись — начинаем с чистого состояния
  engine.reset()
  await refreshActiveEntry()
  emit('entry-created', entry.id)
}

// Продолжить заполнение существующей записи (в т.ч. другим сотрудником)
async function resumeEntry(entryId: string) {
  selectedEntryId.value = entryId
  showEntriesList.value = false
  // Восстанавливаем сохранённый прогресс, НЕ обнуляя его
  const entry = await getEntry(entryId)
  engine.load(entry)
  await refreshActiveEntry()
}

// Закрыть запись — прогресс уже сохранён, просто возвращаемся к списку
function closeEntry() {
  selectedEntryId.value = null
  activeEntry.value = null
  showEntriesList.value = false
}

// Подтверждение удаления записи (окно приподнято над карточкой исследования).
const deleteEntryTarget = ref<JournalEntry | null>(null)
const deleteEntryOpen = ref(false)

function askDeleteEntry(entry: JournalEntry) {
  deleteEntryTarget.value = entry
  deleteEntryOpen.value = true
}

async function confirmDeleteEntry() {
  const entryId = deleteEntryTarget.value?.id
  if (!entryId) {
    return
  }
  await deleteEntry(entryId)
  if (selectedEntryId.value === entryId) {
    selectedEntryId.value = null
    activeEntry.value = null
    engine.reset()
  }
  await loadEntries()
  deleteEntryOpen.value = false
  deleteEntryTarget.value = null
}

async function exportCurrentEntry() {
  if (!selectedEntryId.value) return
  const entry = await getEntry(selectedEntryId.value)
  if (!entry) return
  const json = JSON.stringify(entry, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${entry.title || 'journal-entry'}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="mx-auto w-full max-w-4xl">
    <!-- Выбор или создание записи -->
    <div v-if="!selectedEntryId || showEntriesList" class="mx-auto max-w-xl">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-semibold">
          Записи журнала
        </h3>
        <UButton size="sm" icon="i-lucide-plus" @click="openNewEntryModal">
          Новая запись
        </UButton>
      </div>

      <div v-if="entries.length" class="space-y-2">
        <UCard
          v-for="entry in entries"
          :key="entry.id"
          class="cursor-pointer hover:bg-muted/50 transition-colors"
          @click="resumeEntry(entry.id)"
        >
          <div class="flex items-center justify-between">
            <div>
              <div class="font-medium">
                {{ entry.title }}
              </div>
              <div class="text-xs text-muted">
                {{ new Date(entry.startedAt).toLocaleDateString() }} —
                <UBadge
                  :color="entry.status === 'completed' ? 'success' : 'warning'"
                  variant="subtle"
                  size="xs"
                >
                  {{ entry.status === 'completed' ? 'Завершено' : 'Черновик' }}
                </UBadge>
              </div>
            </div>
            <UButton
              size="xs"
              color="error"
              variant="ghost"
              icon="i-lucide-trash-2"
              @click.stop="askDeleteEntry(entry)"
            />
          </div>
        </UCard>
      </div>
      <p v-else class="text-sm text-muted">
        Пока нет записей. Создайте первую.
      </p>
    </div>

    <!-- Активная запись: форма + боковая панель истории -->
    <div
      v-if="selectedEntryId && !showEntriesList"
      class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]"
    >
      <UCard>
        <template #header>
          <div class="flex items-center justify-between gap-2">
            <div class="min-w-0">
              <h2 class="font-semibold truncate">
                {{ currentEntry?.title }}
              </h2>
              <div class="text-xs text-muted mt-0.5">
                {{ schema.title }} · Версия {{ schema.version }}
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <UBadge v-if="!engine.isFinished.value" color="neutral" variant="subtle">
                Шаг {{ engine.history.value.length + 1 }}
              </UBadge>
              <UButton
                size="xs"
                variant="ghost"
                icon="i-lucide-x"
                @click="closeEntry"
              >
                Закрыть
              </UButton>
            </div>
          </div>
          <!-- Прогресс -->
          <div v-if="!engine.isFinished.value" class="mt-3">
            <UProgress :model-value="engine.progress.value" size="sm" />
            <p class="mt-1 text-xs text-muted">
              {{ engine.progress.value }}% выполнено
            </p>
          </div>
        </template>

        <template v-if="!engine.isFinished.value">
          <h3 class="text-base font-medium mb-1">
            {{ stepData.label }}
          </h3>
          <p v-if="stepData.description" class="text-sm text-muted mb-4">
            {{ stepData.description }}
          </p>

          <WorkflowScreenRenderer
            v-model="engine.answers.value"
            :screen="engine.currentScreen.value"
            :run-id="selectedEntryId"
          />

          <!-- Отказ доменного действия шага (например, запрет перехода) -->
          <UAlert
            v-if="actionError"
            class="mt-4"
            color="error"
            variant="subtle"
            icon="i-lucide-circle-alert"
            title="Действие шага не выполнено"
            :description="actionError"
          />

          <!-- Циклическая нода: врач добавляет произвольное число итераций
             (напр. доп. тесты) и сам решает, когда выйти -->
          <div
            v-if="engine.currentLoop.value"
            class="mt-5 rounded-lg border border-dashed border-success/40 bg-success/5 p-3.5"
          >
            <div class="mb-2.5 flex items-center gap-1.5 text-xs font-semibold text-muted">
              <UIcon name="i-lucide-repeat" class="size-4 text-success" />
              <span>Добавлено: {{ engine.loopItems.value.length }}</span>
            </div>

            <div v-if="engine.loopItems.value.length" class="flex flex-col gap-1.5">
              <div
                v-for="(item, i) in engine.loopItems.value"
                :key="i"
                class="flex items-center gap-2 rounded-md border border-default bg-default px-2 py-1.5"
              >
                <UBadge
                  :label="String(i + 1)"
                  color="success"
                  variant="soft"
                  size="sm"
                />
                <span class="min-w-0 flex-1 truncate text-xs">{{ loopItemSummary(item) }}</span>
                <UButton
                  size="xs"
                  color="error"
                  variant="ghost"
                  icon="i-lucide-x"
                  @click="engine.removeLoopItem(i)"
                />
              </div>
            </div>
            <p v-else class="text-xs text-muted">
              Пока ничего не добавлено. Число {{ engine.currentLoop.value.itemNoun || 'итераций' }} — на ваше усмотрение:
              добавьте сколько нужно или сразу нажмите «Далее».
            </p>

            <UButton
              class="mt-3"
              variant="soft"
              color="success"
              icon="i-lucide-plus"
              :label="`Добавить ${engine.currentLoop.value.itemNoun || 'запись'}`"
              :disabled="!engine.canAddLoopItem.value"
              @click="engine.addLoopItem()"
            />
          </div>

          <!-- Комментарии к текущему шагу -->
          <div class="mt-6 border-t border-default pt-4">
            <div class="mb-2.5 flex items-center gap-1.5 text-sm font-semibold text-highlighted">
              <UIcon name="i-lucide-message-square" class="size-4" />
              <span>Комментарии к шагу</span>
              <UBadge v-if="currentNodeComments.length" size="xs" variant="subtle">
                {{ currentNodeComments.length }}
              </UBadge>
            </div>
            <div v-if="currentNodeComments.length" class="mb-3 flex flex-col gap-2">
              <div
                v-for="c in currentNodeComments"
                :key="c.id"
                class="rounded-lg border border-default bg-elevated/50 px-2.5 py-2"
              >
                <div class="mb-0.5 flex items-baseline gap-2">
                  <span class="text-xs font-semibold text-highlighted">{{ c.author }}</span>
                  <span class="text-[10.5px] text-dimmed">{{ formatDateTime(c.createdAt) }}</span>
                </div>
                <p class="whitespace-pre-wrap break-words text-xs leading-relaxed">
                  {{ c.text }}
                </p>
              </div>
            </div>
            <p v-else class="mb-2 text-xs text-muted">
              Комментариев к этому шагу пока нет.
            </p>
            <div class="flex items-start gap-2">
              <UTextarea
                v-model="newComment"
                :rows="2"
                placeholder="Комментарий к шагу… (Ctrl+Enter — отправить)"
                class="flex-1"
                @keydown.ctrl.enter="submitComment"
              />
              <UButton
                icon="i-lucide-send"
                label="Отправить"
                :disabled="!newComment.trim()"
                @click="submitComment"
              />
            </div>
          </div>
        </template>

        <template v-else>
          <div class="py-8 text-center">
            <UIcon name="i-lucide-circle-check-big" class="mx-auto size-10 text-success" />
            <p class="mt-2 font-medium">
              Журнал заполнен
            </p>
            <p class="text-sm text-muted">
              Все данные сохранены автоматически. Выгрузить результат можно кнопкой «Экспорт JSON».
            </p>
          </div>
        </template>

        <template #footer>
          <div class="flex justify-between items-center">
            <div class="flex gap-2">
              <UButton variant="ghost" :disabled="!engine.history.value.length" @click="engine.goBack">
                Назад
              </UButton>
              <UButton
                v-if="engine.isFinished.value"
                variant="soft"
                color="neutral"
                icon="i-lucide-download"
                @click="exportCurrentEntry"
              >
                Экспорт JSON
              </UButton>
            </div>
            <UButton
              v-if="!engine.isFinished.value"
              :disabled="!engine.canGoNext.value"
              :icon="engine.currentLoop.value ? 'i-lucide-log-out' : undefined"
              @click="onNext"
            >
              {{ engine.currentLoop.value ? 'Завершить и далее' : 'Далее' }}
            </UButton>
            <UButton
              v-else
              variant="soft"
              color="neutral"
              icon="i-lucide-list"
              @click="closeEntry"
            >
              К списку записей
            </UButton>
          </div>
        </template>
      </UCard>

      <!-- Боковая панель: кто заполняет + история изменений -->
      <aside class="flex flex-col gap-4 lg:sticky lg:top-3">
        <UCard :ui="{ body: 'p-4 sm:p-4' }">
          <dl class="flex flex-col gap-1.5 text-xs">
            <div class="flex items-center justify-between gap-2">
              <dt class="text-muted">
                Статус
              </dt>
              <dd>
                <UBadge
                  :color="entryStatusColor(currentEntry?.status)"
                  :label="entryStatusLabel(currentEntry?.status)"
                  variant="subtle"
                  size="sm"
                />
              </dd>
            </div>
            <div class="flex items-center justify-between gap-2">
              <dt class="text-muted">
                Создал(а)
              </dt>
              <dd class="font-medium text-highlighted">
                {{ currentEntry?.createdBy || '—' }}
              </dd>
            </div>
            <div class="flex items-center justify-between gap-2">
              <dt class="text-muted">
                Создано
              </dt>
              <dd>{{ formatDateTime(currentEntry?.startedAt) }}</dd>
            </div>
            <div class="flex items-center justify-between gap-2">
              <dt class="text-muted">
                Последнее изм.
              </dt>
              <dd class="font-medium text-highlighted">
                {{ currentEntry?.updatedBy || '—' }}
              </dd>
            </div>
            <div class="flex items-center justify-between gap-2">
              <dt class="text-muted">
                Обновлено
              </dt>
              <dd>{{ formatDateTime(currentEntry?.updatedAt) }}</dd>
            </div>
          </dl>
          <USeparator class="my-3" />
          <div class="flex items-center gap-1.5 text-xs text-muted">
            <UIcon name="i-lucide-user" class="size-3.5" />
            <span>Вы: <strong class="text-highlighted">{{ currentUser || 'не указано' }}</strong></span>
          </div>
        </UCard>

        <UCard :ui="{ body: 'p-4 sm:p-4' }">
          <div class="mb-3 flex items-center gap-1.5 text-sm font-semibold text-highlighted">
            <UIcon name="i-lucide-history" class="size-4" />
            <span>История</span>
          </div>
          <UTimeline
            v-if="historyItems.length"
            :items="historyItems"
            size="xs"
            color="neutral"
            :ui="{ date: 'text-dimmed', title: 'text-xs font-normal text-default' }"
          />
          <p v-else class="text-xs text-muted">
            Событий пока нет.
          </p>
        </UCard>
      </aside>
    </div>

    <!-- Модалка новой записи -->
    <UModal v-model:open="showNewEntryModal" title="Новая запись журнала">
      <template #body>
        <UFormField label="Название записи" required>
          <UInput v-model="newEntryTitle" placeholder="например: Проба №47 от 15.07" @keyup.enter="startNewEntry" />
        </UFormField>
      </template>
      <template #footer>
        <UButton variant="ghost" @click="showNewEntryModal = false">
          Отмена
        </UButton>
        <UButton :disabled="!newEntryTitle.trim()" @click="startNewEntry">
          Создать
        </UButton>
      </template>
    </UModal>

    <!-- Подтверждение удаления записи -->
    <ConfirmDialog
      v-model:open="deleteEntryOpen"
      elevated
      title="Удалить запись"
      :description="`Удалить запись «${deleteEntryTarget?.title ?? ''}»? Действие необратимо.`"
      confirm-label="Удалить"
      confirm-color="error"
      confirm-icon="i-lucide-trash-2"
      @confirm="confirmDeleteEntry"
    />
  </div>
</template>
