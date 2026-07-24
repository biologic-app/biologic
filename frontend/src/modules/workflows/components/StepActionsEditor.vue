<script setup lang="ts">
// components/StepActionsEditor.vue
// Редактор доменных действий шага (US-007, schema-doc §6). Настраивает
// data.actions[] step-ноды без правки JSON: выбор команды из реестра
// (engine/action-commands.ts), источник id цели (scope/поле) и маппинг
// аргументов команды на ответы/константы/актора. Исполнение — только на сервере
// через execute-step; здесь лишь конфигурация DomainAction.

import { computed } from 'vue'
import { ACTION_COMMANDS, findActionCommand } from '@/modules/workflows/engine/action-commands'
import type { AnswerRef, DomainAction } from '@/modules/workflows/types/journal'

const actions = defineModel<DomainAction[]>({ default: () => [] })

const props = defineProps<{
  // Поля схемы (все step/loop-экраны) для выбора targetField и ссылок на ответы.
  fieldOptions: Array<{ label: string, value: string }>
}>()

const commandItems = ACTION_COMMANDS.map((command) => ({ label: command.label, value: command.key }))

const TARGET_FROM_ITEMS = [
  { label: 'Область (scope)', value: 'scope' as const },
  { label: 'Поле шага', value: 'field' as const },
]

// Тип ссылки аргумента + служебное значение «не задано» (аргумент опускается).
type RefKind = 'unset' | 'answer' | 'const' | 'actor'
const REF_KIND_ITEMS: Array<{ label: string, value: RefKind }> = [
  { label: 'Не задано', value: 'unset' },
  { label: 'Из ответа', value: 'answer' },
  { label: 'Константа', value: 'const' },
  { label: 'Текущий пользователь', value: 'actor' },
]

let idCounter = 0
function nextActionId(): string {
  idCounter += 1
  return `action-${Date.now().toString(36)}-${idCounter}`
}

function addAction() {
  const first = ACTION_COMMANDS[0]
  const action: DomainAction = {
    id: nextActionId(),
    label: first.label,
    command: first.key,
    targetFrom: 'field',
    targetField: props.fieldOptions[0]?.value ?? '',
    argsMapping: {},
  }
  actions.value = [...actions.value, action]
}

function removeAction(index: number) {
  actions.value = actions.value.filter((_, i) => i !== index)
}

// Смена команды: подпись по умолчанию берём из реестра, если автор её не менял.
function onCommandChange(action: DomainAction, command: string) {
  const previous = findActionCommand(action.command)
  action.command = command
  if (!action.label || action.label === previous?.label) {
    action.label = findActionCommand(command)?.label ?? action.label
  }
}

function commandDef(action: DomainAction) {
  return findActionCommand(action.command)
}

function refKind(action: DomainAction, argKey: string): RefKind {
  return action.argsMapping[argKey]?.from ?? 'unset'
}

function setRefKind(action: DomainAction, argKey: string, kind: RefKind) {
  if (kind === 'unset') {
    const next = { ...action.argsMapping }
    delete next[argKey]
    action.argsMapping = next
    return
  }
  const ref: AnswerRef =
    kind === 'actor'
      ? { from: 'actor' }
      : kind === 'const'
        ? { from: 'const', value: '' }
        : { from: 'answer', fieldId: props.fieldOptions[0]?.value ?? '' }
  action.argsMapping = { ...action.argsMapping, [argKey]: ref }
}

function answerFieldId(action: DomainAction, argKey: string): string {
  const ref = action.argsMapping[argKey]
  return ref?.from === 'answer' ? ref.fieldId : ''
}

function setAnswerFieldId(action: DomainAction, argKey: string, fieldId: string) {
  action.argsMapping = { ...action.argsMapping, [argKey]: { from: 'answer', fieldId } }
}

function constValue(action: DomainAction, argKey: string): string {
  const ref = action.argsMapping[argKey]
  return ref?.from === 'const' ? String(ref.value) : ''
}

function setConstValue(action: DomainAction, argKey: string, value: string) {
  action.argsMapping = { ...action.argsMapping, [argKey]: { from: 'const', value } }
}

const hasFields = computed(() => props.fieldOptions.length > 0)
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-1.5 text-xs font-semibold text-muted">
        <UIcon name="i-lucide-zap" class="size-3.5" />
        <span>Действия при завершении шага</span>
        <UBadge v-if="actions.length" size="xs" variant="subtle">
          {{ actions.length }}
        </UBadge>
      </div>
      <UButton
        size="xs"
        variant="ghost"
        icon="i-lucide-plus"
        label="Действие"
        @click="addAction"
      />
    </div>

    <p v-if="!actions.length" class="text-[11px] text-dimmed">
      Нет действий. При завершении шага можно вызвать доменную команду (например,
      «Завершить тест») — id цели и аргументы берутся из ответов.
    </p>

    <div
      v-for="(action, ai) in actions"
      :key="action.id"
      class="flex flex-col gap-2.5 rounded-lg border border-default bg-elevated/30 p-3"
    >
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-semibold text-highlighted">{{ action.label || 'Действие' }}</span>
        <UButton
          size="xs"
          color="error"
          variant="ghost"
          icon="i-lucide-trash-2"
          @click="removeAction(ai)"
        />
      </div>

      <UFormField label="Подпись" size="xs">
        <UInput v-model="action.label" size="xs" class="w-full" />
      </UFormField>

      <UFormField label="Команда" size="xs">
        <USelect
          :model-value="action.command"
          :items="commandItems"
          value-key="value"
          size="xs"
          class="w-full"
          @update:model-value="(v: string) => onCommandChange(action, v)"
        />
        <template #help>
          <span v-if="commandDef(action)" class="text-[10.5px] text-dimmed">
            Требует статус цели: {{ commandDef(action)!.preconditionStatuses.join(', ') }}
          </span>
        </template>
      </UFormField>

      <UFormField label="Id цели" size="xs">
        <USelect
          v-model="action.targetFrom"
          :items="TARGET_FROM_ITEMS"
          value-key="value"
          size="xs"
          class="w-full"
        />
      </UFormField>

      <UFormField v-if="action.targetFrom === 'field'" label="Поле с id цели" size="xs">
        <USelect
          v-if="hasFields"
          v-model="action.targetField"
          :items="fieldOptions"
          value-key="value"
          size="xs"
          class="w-full"
        />
        <UInput
          v-else
          v-model="action.targetField"
          size="xs"
          placeholder="test_id"
          class="w-full"
        />
      </UFormField>

      <!-- Маппинг аргументов команды -->
      <template v-if="commandDef(action)">
        <span class="text-[10px] font-semibold uppercase tracking-wide text-dimmed">
          Аргументы
        </span>
        <div
          v-for="arg in commandDef(action)!.args"
          :key="arg.key"
          class="flex flex-col gap-1.5 rounded-md border border-default p-2"
        >
          <div class="flex items-center gap-1.5">
            <span class="min-w-0 flex-1 truncate text-xs text-muted">
              {{ arg.label }}
              <span v-if="arg.required" class="text-error">*</span>
            </span>
            <USelect
              :model-value="refKind(action, arg.key)"
              :items="REF_KIND_ITEMS"
              value-key="value"
              size="xs"
              class="w-40"
              @update:model-value="(v: RefKind) => setRefKind(action, arg.key, v)"
            />
          </div>
          <USelect
            v-if="refKind(action, arg.key) === 'answer' && hasFields"
            :model-value="answerFieldId(action, arg.key)"
            :items="fieldOptions"
            value-key="value"
            size="xs"
            class="w-full"
            @update:model-value="(v: string) => setAnswerFieldId(action, arg.key, v)"
          />
          <UInput
            v-else-if="refKind(action, arg.key) === 'answer'"
            :model-value="answerFieldId(action, arg.key)"
            size="xs"
            placeholder="fieldId"
            class="w-full"
            @update:model-value="(v: string) => setAnswerFieldId(action, arg.key, v)"
          />
          <UInput
            v-else-if="refKind(action, arg.key) === 'const'"
            :model-value="constValue(action, arg.key)"
            size="xs"
            placeholder="Значение"
            class="w-full"
            @update:model-value="(v: string) => setConstValue(action, arg.key, v)"
          />
        </div>
      </template>
    </div>
  </div>
</template>
