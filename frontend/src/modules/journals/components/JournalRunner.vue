<script setup lang="ts">
// components/journal/JournalRunner.vue
// UI для заполнения журнала с сохранением прогресса и управлением записями

import { computed, ref } from 'vue';
import ConfirmDialog from '@/shared/ui/ConfirmDialog.vue';
import { useJournalUser } from '@/modules/journals/composables/useJournalUser';
import { useJournalEngine } from '@/modules/journals/composables/useJournalEngine';
import { addComment, createEntry, deleteEntry, getEntriesForSchema, getEntry, logActivity, saveEntryProgress } from '@/modules/journals/composables/useJournalStorage';
import type { JournalActivityType, JournalEntry, JournalSchema, JournalStepData } from '@/modules/journals/types/journal';

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

// Управление записями
const showNewEntryModal = ref(false)
const newEntryTitle = ref('')
const selectedEntryId = ref<string | null>(null)
const showEntriesList = ref(false)
const newComment = ref('')

// Список записей (перечитывается при tick)
const listTick = ref(0)
const entries = computed(() => {
  void listTick.value // зависимость для ручного обновления
  return getEntriesForSchema(props.templateId, props.schema.version, props.scope)
})

// Актуальный снимок открытой записи (мета/комментарии/история) —
// перечитываем из хранилища после каждого изменения
const activeEntry = ref<JournalEntry | null>(null)
function refreshActiveEntry() {
  activeEntry.value = selectedEntryId.value ? getEntry(selectedEntryId.value) ?? null : null
  listTick.value++
}
const currentEntry = computed(() => activeEntry.value ?? undefined)

// Движок
const engine = useJournalEngine(props.schema, {
  entryId: selectedEntryId.value || undefined,
  onSave: (answers, history, currentNodeId, loops) => {
    if (selectedEntryId.value) {
      saveEntryProgress(selectedEntryId.value, answers, history, currentNodeId, loops, authorName())
      refreshActiveEntry()
    }
  },
})

// Комментарии к текущему шагу
const currentNodeId = computed(() => engine.currentStep.value.id)
const currentNodeComments = computed(() =>
  (activeEntry.value?.comments ?? []).filter((c) => c.nodeId === currentNodeId.value),
)

function submitComment() {
  const text = newComment.value.trim()
  if (!text || !selectedEntryId.value) return
  addComment(selectedEntryId.value, currentNodeId.value, authorName(), text, stepData.value.label)
  newComment.value = ''
  refreshActiveEntry()
}

// Обёртка «Далее»: фиксируем в истории, кто заполнил шаг
function onNext() {
  if (!engine.canGoNext.value || engine.isFinished.value) return
  const completed = engine.currentStep.value
  engine.goNext()
  if (selectedEntryId.value && engine.currentStep.value.id !== completed.id) {
    logActivity(selectedEntryId.value, 'step_completed', authorName(), {
      nodeId: completed.id,
      label: (completed.data as JournalStepData).label,
    })
    if (engine.isFinished.value) {
      logActivity(selectedEntryId.value, 'completed', authorName())
      emit('entry-completed', selectedEntryId.value)
    }
    refreshActiveEntry()
  }
}

const stepData = computed(() => engine.currentStep.value.data as JournalStepData)

// Краткая сводка одной итерации цикла для списка добавленных
function loopItemSummary(item: Record<string, unknown>): string {
  const fields = engine.currentLoop.value?.fields ?? []
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

function openNewEntryModal() {
  newEntryTitle.value = props.defaultTitle ?? ''
  showNewEntryModal.value = true
}

function startNewEntry() {
  if (!newEntryTitle.value.trim()) return
  const entry = createEntry(props.templateId, props.schema.version, newEntryTitle.value.trim(), authorName(), props.scope)
  selectedEntryId.value = entry.id
  showNewEntryModal.value = false
  newEntryTitle.value = ''
  showEntriesList.value = false
  // Новая запись — начинаем с чистого состояния
  engine.reset()
  refreshActiveEntry()
  emit('entry-created', entry.id)
}

// Продолжить заполнение существующей записи (в т.ч. другим сотрудником)
function resumeEntry(entryId: string) {
  selectedEntryId.value = entryId
  showEntriesList.value = false
  // Восстанавливаем сохранённый прогресс, НЕ обнуляя его
  engine.load(entryId)
  logActivity(entryId, 'reopened', authorName())
  refreshActiveEntry()
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

function confirmDeleteEntry() {
  const entryId = deleteEntryTarget.value?.id
  if (!entryId) {
    return
  }
  deleteEntry(entryId)
  if (selectedEntryId.value === entryId) {
    selectedEntryId.value = null
    activeEntry.value = null
    engine.reset()
  }
  listTick.value++
  deleteEntryOpen.value = false
  deleteEntryTarget.value = null
}

function exportCurrentEntry() {
  if (!selectedEntryId.value) return
  const entry = getEntry(selectedEntryId.value)
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
  <div class="journal-runner-wrapper">
    <!-- Выбор или создание записи -->
    <div v-if="!selectedEntryId || showEntriesList" class="mb-6">
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
    <div v-if="selectedEntryId && !showEntriesList" class="journal-entry">
      <UCard class="journal-entry__main">
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
          <!-- Прогресс-бар -->
          <div v-if="!engine.isFinished.value" class="mt-3">
            <div class="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                class="h-full bg-primary transition-all duration-300 rounded-full"
                :style="{ width: `${engine.progress.value}%` }"
              />
            </div>
            <div class="text-xs text-muted mt-1">
              {{ engine.progress.value }}% выполнено
            </div>
          </div>
        </template>

        <template v-if="!engine.isFinished.value">
          <h3 class="text-base font-medium mb-1">
            {{ stepData.label }}
          </h3>
          <p v-if="stepData.description" class="text-sm text-muted mb-4">
            {{ stepData.description }}
          </p>

          <div class="space-y-4">
            <UFormField
              v-for="field in engine.currentFields.value"
              :key="field.id"
              :label="field.label"
              :required="field.required"
            >
              <template v-if="field.type === 'text'">
                <UInput v-model="engine.answers.value[field.id] as string" :placeholder="field.placeholder" />
              </template>
              <template v-else-if="field.type === 'textarea'">
                <UTextarea v-model="engine.answers.value[field.id] as string" :placeholder="field.placeholder" :rows="3" />
              </template>
              <template v-else-if="field.type === 'number'">
                <UInput v-model.number="engine.answers.value[field.id] as number" type="number" />
              </template>
              <template v-else-if="field.type === 'boolean'">
                <USwitch v-model="engine.answers.value[field.id] as boolean" />
              </template>
              <template v-else-if="field.type === 'select'">
                <USelect
                  v-model="engine.answers.value[field.id] as string"
                  :items="field.options?.map(o => ({ label: o.label, value: o.value })) ?? []"
                />
              </template>
              <template v-else-if="field.type === 'date'">
                <UInput v-model="engine.answers.value[field.id] as string" type="date" />
              </template>
            </UFormField>
          </div>

          <!-- Циклическая нода: врач добавляет произвольное число итераций
             (напр. доп. тесты) и сам решает, когда выйти -->
          <div v-if="engine.currentLoop.value" class="journal-loop">
            <div class="journal-loop__head">
              <UIcon name="i-lucide-repeat" class="size-4 text-success" />
              <span>Добавлено: {{ engine.loopItems.value.length }}</span>
            </div>

            <div v-if="engine.loopItems.value.length" class="journal-loop__list">
              <div v-for="(item, i) in engine.loopItems.value" :key="i" class="journal-loop__item">
                <span class="journal-loop__badge">{{ i + 1 }}</span>
                <span class="journal-loop__item-text">{{ loopItemSummary(item) }}</span>
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
              :disabled="!engine.canAddLoopItem.value"
              @click="engine.addLoopItem()"
            >
              Добавить {{ engine.currentLoop.value.itemNoun || 'запись' }}
            </UButton>
          </div>

          <!-- Комментарии к текущему шагу -->
          <div class="journal-comments">
            <div class="journal-comments__head">
              <UIcon name="i-lucide-message-square" class="size-4" />
              <span>Комментарии к шагу</span>
              <UBadge v-if="currentNodeComments.length" size="xs" variant="subtle">
                {{ currentNodeComments.length }}
              </UBadge>
            </div>
            <div v-if="currentNodeComments.length" class="journal-comments__list">
              <div v-for="c in currentNodeComments" :key="c.id" class="journal-comments__item">
                <div class="journal-comments__meta">
                  <span class="journal-comments__author">{{ c.author }}</span>
                  <span class="journal-comments__time">{{ formatDateTime(c.createdAt) }}</span>
                </div>
                <p class="journal-comments__text">
                  {{ c.text }}
                </p>
              </div>
            </div>
            <p v-else class="text-xs text-muted mb-2">
              Комментариев к этому шагу пока нет.
            </p>
            <div class="journal-comments__form">
              <UTextarea
                v-model="newComment"
                :rows="2"
                placeholder="Комментарий к шагу… (Ctrl+Enter — отправить)"
                class="flex-1"
                @keydown.ctrl.enter="submitComment"
              />
              <UButton icon="i-lucide-send" :disabled="!newComment.trim()" @click="submitComment">
                Отправить
              </UButton>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="journal-runner__done">
            <UIcon name="i-lucide-circle-check-big" class="size-10 text-success" />
            <p class="font-medium mt-2">
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
      <aside class="journal-entry__side">
        <UCard class="journal-side-card">
          <div class="journal-meta">
            <div class="journal-meta__row">
              <span>Статус</span>
              <UBadge :color="currentEntry?.status === 'completed' ? 'success' : 'warning'" variant="subtle" size="xs">
                {{ currentEntry?.status === 'completed' ? 'Завершено' : 'Черновик' }}
              </UBadge>
            </div>
            <div class="journal-meta__row">
              <span>Создал(а)</span><strong>{{ currentEntry?.createdBy || '—' }}</strong>
            </div>
            <div class="journal-meta__row">
              <span>Создано</span><span>{{ formatDateTime(currentEntry?.startedAt) }}</span>
            </div>
            <div class="journal-meta__row">
              <span>Последнее изм.</span><strong>{{ currentEntry?.updatedBy || '—' }}</strong>
            </div>
            <div class="journal-meta__row">
              <span>Обновлено</span><span>{{ formatDateTime(currentEntry?.updatedAt) }}</span>
            </div>
          </div>
          <div class="journal-meta__you">
            <UIcon name="i-lucide-user" class="size-3.5" />
            Вы: <strong>{{ currentUser || 'не указано' }}</strong>
          </div>
        </UCard>

        <UCard class="journal-side-card">
          <div class="journal-history__head">
            <UIcon name="i-lucide-history" class="size-4" />
            <span>История</span>
          </div>
          <div v-if="activityLog.length" class="journal-history">
            <div v-for="ev in activityLog" :key="ev.id" class="journal-history__item">
              <span class="journal-history__icon" :class="activityMeta[ev.type].color">
                <UIcon :name="activityMeta[ev.type].icon" class="size-3.5" />
              </span>
              <div class="journal-history__body">
                <p class="journal-history__text">
                  <strong>{{ ev.author }}</strong> {{ activityMeta[ev.type].verb }}<template v-if="ev.label">
                    «{{ ev.label }}»
                  </template>
                </p>
                <span class="journal-history__time">{{ formatDateTime(ev.at) }}</span>
              </div>
            </div>
          </div>
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

<style scoped>
.journal-runner-wrapper {
  max-width: 62rem;
  margin: 0 auto;
}
/* Список записей держим узким и по центру */
.journal-runner-wrapper > .mb-6 {
  max-width: 34rem;
  margin-left: auto;
  margin-right: auto;
}
/* Активная запись: форма + боковая панель */
.journal-entry {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  align-items: start;
}
.journal-entry__side {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 12px;
}
@media (max-width: 860px) {
  .journal-entry {
    grid-template-columns: 1fr;
  }
  .journal-entry__side {
    position: static;
  }
}
.journal-runner__done {
  text-align: center;
  padding: 2rem 0;
}

/* ─── Циклическая нода ─────────────────────────────────────────────── */
.journal-loop {
  margin-top: 20px;
  padding: 14px;
  border: 1px dashed color-mix(in oklab, var(--ui-success) 45%, var(--ui-border));
  border-radius: 12px;
  background: color-mix(in oklab, var(--ui-success) 5%, transparent);
}
.journal-loop__head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ui-text-muted);
  margin-bottom: 10px;
}
.journal-loop__list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.journal-loop__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
}
.journal-loop__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--ui-success);
  background: color-mix(in oklab, var(--ui-success) 15%, transparent);
}
.journal-loop__item-text {
  flex: 1;
  min-width: 0;
  font-size: 12.5px;
  color: var(--ui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ─── Комментарии к шагу ───────────────────────────────────────────── */
.journal-comments {
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid var(--ui-border);
}
.journal-comments__head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ui-text-highlighted);
  margin-bottom: 10px;
}
.journal-comments__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}
.journal-comments__item {
  padding: 8px 10px;
  border-radius: 10px;
  background: var(--ui-bg-muted);
  border: 1px solid var(--ui-border);
}
.journal-comments__meta {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 2px;
}
.journal-comments__author {
  font-size: 12px;
  font-weight: 600;
  color: var(--ui-text-highlighted);
}
.journal-comments__time {
  font-size: 10.5px;
  color: var(--ui-text-dimmed);
}
.journal-comments__text {
  font-size: 12.5px;
  line-height: 1.4;
  color: var(--ui-text);
  white-space: pre-wrap;
  word-break: break-word;
}
.journal-comments__form {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

/* ─── Мета записи ──────────────────────────────────────────────────── */
.journal-meta {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.journal-meta__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12.5px;
  color: var(--ui-text-muted);
}
.journal-meta__row strong {
  color: var(--ui-text-highlighted);
  font-weight: 600;
}
.journal-meta__you {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--ui-border);
  font-size: 12px;
  color: var(--ui-text-muted);
}

/* ─── История изменений ────────────────────────────────────────────── */
.journal-history__head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ui-text-highlighted);
  margin-bottom: 12px;
}
.journal-history {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 340px;
  overflow-y: auto;
}
.journal-history__item {
  display: flex;
  gap: 9px;
  align-items: flex-start;
}
.journal-history__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border-radius: 7px;
  background: var(--ui-bg-muted);
  border: 1px solid var(--ui-border);
}
.journal-history__body {
  min-width: 0;
}
.journal-history__text {
  font-size: 12px;
  line-height: 1.35;
  color: var(--ui-text);
}
.journal-history__text strong {
  color: var(--ui-text-highlighted);
  font-weight: 600;
}
.journal-history__time {
  font-size: 10.5px;
  color: var(--ui-text-dimmed);
}
</style>