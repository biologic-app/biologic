<script setup lang="ts">
import { reactive } from "vue";
import { useI18n } from "vue-i18n";
import { CalendarDateTime, getLocalTimeZone, parseDateTime } from "@internationalized/date";
import { formatDisplay, type DetailFieldValue } from "@/shared/ui/entity-detail.helpers";
import StatusBadge from "@/shared/ui/StatusBadge.vue";
import StatusColorPicker from "@/shared/ui/StatusColorPicker.vue";
import { statusColorName } from "@/shared/i18n/status-label";

export type FieldOption = { label: string; value: DetailFieldValue };

export type GridField = {
  key: string;
  label: string;
  type?: "text" | "number" | "textarea" | "boolean" | "select" | "password" | "date" | "color";
  required?: boolean;
  // По умолчанию поле редактируемо; readonly-поля показываются только в просмотре.
  editable?: boolean;
  // Инлайновые опции select (иначе берутся из referenceOptions по ключу).
  options?: FieldOption[];
  // Разрешить очистку select (кнопка сброса значения).
  clearable?: boolean;
  // Сырое значение записи для режима просмотра.
  value?: unknown;
};

// Универсальная сетка полей карточки (просмотр/редактирование) в виде <dl>.
// Объединяет разметку, ранее продублированную в EntityDetailDialogBase,
// AccessEntityDetailModal и DictionaryCrudDetailModal. Значения формы хранит
// родитель (через useEntityForm); грид только рендерит и эмитит изменения.
const props = withDefaults(
  defineProps<{
    fields: GridField[];
    editing: boolean;
    formState: Record<string, DetailFieldValue>;
    referenceOptions?: Record<string, FieldOption[]>;
    // Кастомный вывод значения в просмотре (например, разрешение связи _id → название).
    resolveDisplay?: (field: GridField) => string;
    // Кастомная проверка редактируемости поля (по умолчанию field.editable ?? true).
    isEditable?: (field: GridField) => boolean;
  }>(),
  {
    referenceOptions: () => ({}),
    resolveDisplay: undefined,
    isEditable: undefined,
  },
);

const emit = defineEmits<{
  (event: "update", key: string, value: unknown): void;
}>();

function editable(field: GridField) {
  if (props.isEditable) return props.isEditable(field);
  return field.editable ?? true;
}

function displayValue(field: GridField) {
  if (props.resolveDisplay) return props.resolveDisplay(field);
  return formatDisplay(field.value);
}

function formString(key: string) {
  const value = props.formState[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function formBoolean(key: string) {
  return Boolean(props.formState[key]);
}

function optionValue(key: string) {
  const value = props.formState[key];
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean" || value === null
    ? value
    : undefined;
}

function optionsFor(field: GridField): FieldOption[] {
  return field.options ?? props.referenceOptions[field.key] ?? [];
}

// Токен цвета статуса для просмотра/бейджа: из значения записи (view) либо
// текущего состояния формы (edit).
function colorToken(field: GridField) {
  const value = props.formState[field.key] ?? field.value;
  return typeof value === "string" ? value : null;
}

// Дата хранится в formState как ISO-строка; UInputDate работает с CalendarDateTime.
function calendarDateTime(key: string) {
  const value = props.formState[key];
  if (typeof value !== "string" || !value) return undefined;
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return undefined;
    return new CalendarDateTime(
      date.getFullYear(),
      date.getMonth() + 1,
      date.getDate(),
      date.getHours(),
      date.getMinutes(),
      date.getSeconds(),
    );
  } catch {
    return undefined;
  }
}

function setCalendarDateTime(key: string, value: unknown) {
  if (!value) {
    emit("update", key, null);
    return;
  }
  const dateTime = "toDate" in (value as object)
    ? (value as CalendarDateTime)
    : parseDateTime(String(value));
  emit("update", key, dateTime.toDate(getLocalTimeZone()).toISOString());
}

const dateInputRefs = reactive<Record<string, { inputsRef?: { $el: HTMLElement }[] } | null>>({});
function setDateInputRef(key: string, el: unknown) {
  dateInputRefs[key] = el as { inputsRef?: { $el: HTMLElement }[] } | null;
}

const { t } = useI18n();
</script>

<template>
  <div class="overflow-hidden rounded-lg border border-default">
    <dl class="grid text-sm md:grid-cols-2">
      <div
        v-for="field in fields"
        :key="field.key"
        class="grid grid-cols-[9.5rem_minmax(0,1fr)] border-b border-default last:border-b-0 md:[&:nth-last-child(-n+2)]:border-b-0 md:odd:border-e"
      >
        <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
          {{ field.label }}<span v-if="editing && field.required" class="text-error"> *</span>
        </dt>
        <dd class="min-w-0 px-3 py-2 text-muted">
          <template v-if="editing && editable(field)">
            <UTextarea
              v-if="field.type === 'textarea'"
              :model-value="formString(field.key)"
              autoresize
              :rows="2"
              @update:model-value="emit('update', field.key, $event)"
            />
            <USwitch
              v-else-if="field.type === 'boolean'"
              :model-value="formBoolean(field.key)"
              @update:model-value="emit('update', field.key, $event)"
            />
            <USelectMenu
              v-else-if="field.type === 'select'"
              :model-value="optionValue(field.key)"
              :items="optionsFor(field)"
              value-key="value"
              label-key="label"
              class="w-full"
              :clear="field.clearable || undefined"
              @update:model-value="emit('update', field.key, $event)"
            />
            <UInputDate
              v-else-if="field.type === 'date'"
              :ref="(el: unknown) => setDateInputRef(field.key, el)"
              :model-value="calendarDateTime(field.key)"
              class="w-full"
              @update:model-value="setCalendarDateTime(field.key, $event)"
            >
              <template #trailing>
                <UPopover :reference="dateInputRefs[field.key]?.inputsRef?.[3]?.$el">
                  <UButton
                    color="neutral"
                    variant="link"
                    size="sm"
                    icon="i-lucide-calendar"
                    :aria-label="t('crud.chooseDate')"
                    class="px-0"
                  />
                  <template #content>
                    <UCalendar
                      :model-value="calendarDateTime(field.key)"
                      class="p-2"
                      @update:model-value="setCalendarDateTime(field.key, $event)"
                    />
                  </template>
                </UPopover>
              </template>
            </UInputDate>
            <StatusColorPicker
              v-else-if="field.type === 'color'"
              :model-value="formString(field.key)"
              @update:model-value="emit('update', field.key, $event)"
            />
            <UInput
              v-else
              :model-value="formString(field.key)"
              :type="field.type === 'number' ? 'number' : field.type === 'password' ? 'password' : 'text'"
              :required="field.required || undefined"
              @update:model-value="emit('update', field.key, $event)"
            />
          </template>
          <StatusBadge
            v-else-if="field.type === 'color'"
            :color="colorToken(field)"
            :label="statusColorName(colorToken(field))"
          />
          <span v-else class="block break-words whitespace-pre-line">
            {{ displayValue(field) }}
          </span>
        </dd>
      </div>
    </dl>
  </div>
</template>
