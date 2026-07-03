<script setup lang="ts">
import { computed, reactive, ref, resolveComponent, watch } from "vue";
import type { TabsItem } from "@nuxt/ui";
import type { CrudModuleConfig } from '@/shared/types/crud';
import {
  apiCreateRequest,
  apiReadListRequest,
  apiReadRequest,
  apiUpdateRequest,
  loadReferenceOptions,
} from "@/shared/api/client.api";
import { usePermission } from "@/shared/composables/usePermission";
import { useAuth } from "@/modules/auth";
import { crudModules } from "@/shared/config/crud-modules";
import CrudFormModal from "@/shared/ui/CrudFormModal.vue";
import ProtocolPreviewModal from "@/shared/ui/ProtocolPreviewModal.vue";
import TechnicalAuditTimeline from "@/shared/ui/TechnicalAuditTimeline.vue";
import EntityRelatedTab from "@/shared/ui/EntityRelatedTab.vue";
import EntityDetailMasterList, { type DetailListItem } from "@/shared/ui/EntityDetailMasterList.vue";
import {
  historyEntryToTechnicalAuditEvent,
  type TechnicalAuditHistoryEntry,
} from "@/shared/ui/technical-audit";
import { formatDateTime } from "@/shared/utils/format";
import { getValueByPath } from "@/shared/utils/object";
import {
  getLastStepperIndex,
  timelineEventsToStepperItems,
  timelineStepperUi,
} from "@/shared/ui/timeline-stepper";
import {
  booleanStatus,
  compact,
  compactEvents,
  entityDisplayCode,
  formatDisplay,
  formatPlain,
  makeEvent,
  namedValue,
  normalizeFormValue,
  pickText,
  type DetailTimelineEvent,
  type EntityKind,
} from "@/shared/ui/entity-detail.helpers";
import { useRelatedEntities } from "@/shared/composables/useRelatedEntities";

type CrudRow = {
  id: string | number;
  [key: string]: unknown;
};

type FieldValue = string | number | boolean | null;
type TimelineEvent = DetailTimelineEvent;

const props = defineProps<{
  open: boolean;
  config: CrudModuleConfig;
  item: CrudRow | null;
  businessKind?: EntityKind | null;
  listItems?: DetailListItem[];
  selectedId?: string | number | null;
  listHasMore?: boolean;
  listLoadingMore?: boolean;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
  (event: "open-related", payload: { kind: EntityKind; item: CrudRow }): void;
  (event: "select", id: string | number): void;
  (event: "list-load-more"): void;
}>();

const UBadge = resolveComponent("UBadge");
const activeTab = ref<"card" | "technical" | "related">("card");
const detail = ref<CrudRow | null>(null);
const auditHistory = ref<TechnicalAuditHistoryEntry[]>([]);
const loading = ref(false);
const saving = ref(false);
const testsSaving = ref(false);
const editing = ref(false);
const fullscreen = ref(false);
const loadError = ref<string | null>(null);
const formState = reactive<Record<string, FieldValue>>({});
const referenceOptions = ref<Record<string, Array<{ label: string; value: FieldValue }>>>({});
const addSampleOpen = ref(false);
const addSampleSaving = ref(false);
const previewOpen = ref(false);

const { can } = usePermission();
const auth = useAuth();

const currentItem = computed(() => detail.value ?? props.item);
const isStatusTracked = computed(() => Boolean(props.businessKind));

// Read-only roles (e.g. sanitary_inspector) must not see an edit affordance
// here even though the row context menu already disables its own
// "Редактировать" item — this in-card button is a separate entry point into
// the same PATCH and was previously ungated.
const canEditEntity = computed(
  () => Boolean(props.businessKind) && can(props.businessKind!, "edit"),
);

// Регистратор добавляет образцы в направление из его карточки, а не со
// страницы «Образцы» (createDisabled там, см. shared/domain/entity-rules.ts).
// Доступно только пока направление в статусе «Черновик».
const canAddSampleToDirection = computed(() => {
  const row = currentItem.value;
  const status = row?.status;
  const statusCode =
    status && typeof status === "object" ? (status as { code?: string }).code : undefined;
  return (
    props.businessKind === "directions" && statusCode === "draft" && can("samples", "create")
  );
});

const sampleCreateFields = computed(() =>
  crudModules.samples.fields.filter((field) => field.key !== "direction_id"),
);

function openAddSample() {
  addSampleOpen.value = true;
}

async function openPreview() {
  if (!relatedRows.value.length) {
    await loadRelatedRows(true);
  }
  previewOpen.value = true;
}

async function saveNewSample(payload: Record<string, unknown>) {
  const row = currentItem.value;
  if (!row) return;

  addSampleSaving.value = true;
  try {
    await apiCreateRequest("/samples", {
      method: "POST",
      body: { ...payload, direction_id: row.id },
    });
    addSampleOpen.value = false;
    await loadRelatedRows(true);
  } finally {
    addSampleSaving.value = false;
  }
}

const {
  relatedRows,
  relatedLoading,
  relatedLoadingMore,
  relatedCursor,
  relatedHasMore,
  loadRelatedRows,
} = useRelatedEntities({
  currentItem: () => currentItem.value,
  businessKind: () => props.businessKind,
});

const modalUi = computed(() => ({
  content: fullscreen.value
    ? "h-[calc(100vh-1rem)] max-w-[calc(100vw-1rem)] overflow-hidden p-0"
    : "h-[82vh] max-h-[860px] min-h-[42rem] max-w-[calc(100vw-2rem)] overflow-hidden p-0 sm:max-w-7xl",
  header: "p-0",
  body: "p-0",
  footer: "p-0",
}));

const tabs = computed<TabsItem[]>(() => [
  { label: "Карточка", icon: "i-lucide-panel-top", value: "card" },
  { label: "Технический аудит", icon: "i-lucide-list", value: "technical" },
  { label: "Связанные", icon: "i-lucide-link", value: "related" },
]);

const title = computed(() => {
  const row = currentItem.value;
  if (!row) return props.config.title;

  if (props.businessKind === "research") {
    return compact([
      relationDisplayLabel(row, "sample"),
      relationDisplayLabel(row, "research_goal"),
    ]).join(" · ") || `${props.config.title} ${entityDisplayCode(row.id)}`;
  }

  return pickText(row, [
    "name",
    "full_name",
    "code",
    "base_no",
    "sample.name",
    "research_goal.name",
    "object.name",
  ]) || `${props.config.title} ${entityDisplayCode(row.id)}`;
});

const subtitle = computed(() => {
  const row = currentItem.value;
  if (!row) return "";

  if (props.businessKind === "directions") {
    return compact([
      row.year_no ? `Год ${row.year_no}` : null,
      row.base_no ? `№ ${row.base_no}` : null,
      namedValue(row.object),
    ]).join(" · ");
  }

  if (props.businessKind === "samples") {
    return compact([
      namedValue(row.sample_type),
      namedValue(row.direction),
      row.mass ? String(row.mass) : null,
    ]).join(" · ");
  }

  if (props.businessKind === "research") {
    return compact([
      relationDisplayLabel(row, "sample"),
      relationDisplayLabel(row, "research_goal"),
      relationDisplayLabel(row, "lab"),
    ]).join(" · ");
  }

  return props.config.description;
});

const statusLabel = computed(() => {
  const row = currentItem.value;
  return row ? relationDisplayLabel(row, "status") || booleanStatus(row) : "";
});

const statusColor = computed(() => {
  const label = statusLabel.value.toLowerCase();

  if (label.includes("заверш") || label.includes("complete") || label.includes("released")) {
    return "success";
  }

  if (label.includes("работ") || label.includes("progress") || label.includes("registered")) {
    return "primary";
  }

  if (label.includes("отклон") || label.includes("reject") || label.includes("error")) {
    return "error";
  }

  return "neutral";
});

const visibleFields = computed(() => {
  const row = currentItem.value;
  if (!row) return [];

  return props.config.fields.map((field) => ({
    ...field,
    value: getValueByPath(row, field.key),
  }));
});

const statusHistory = computed<TimelineEvent[]>(() => {
  const row = currentItem.value;
  if (!row) return [];

  if (props.businessKind === "directions") {
    return compactEvents([
      makeEvent("created", "Создано", "Направление сформировано.", namedValue(row.doctor), row.sampled_at),
      makeEvent("received", "Получено", "Направление принято в обработку.", "registrar", row.received_at),
      row.completed_at ? makeEvent("completed", "Завершено", "Статус переведен в финальное состояние.", "process", row.completed_at) : null,
    ]);
  }

  if (props.businessKind === "samples") {
    return compactEvents([
      makeEvent("created", "Создано", "Образец связан с направлением.", namedValue(row.direction), row.sampled_at ?? row.received_at),
      makeEvent("registered", "Зарегистрировано", "Образец принят в работу.", "registrar", row.received_at),
      row.completed_at ? makeEvent("closed", "Закрыто", row.verdict ? String(row.verdict) : "Статус переведен в финальное состояние.", "process", row.completed_at) : null,
    ]);
  }

  if (props.businessKind === "research") {
    return compactEvents([
      makeEvent("assigned", "Назначено", "Исследование прикреплено к образцу.", relationDisplayLabel(row, "research_goal"), row.created_at ?? row.received_at),
      makeEvent("started", "В работе", "Лаборатория получила исследование.", relationDisplayLabel(row, "lab"), row.received_at),
      row.completed_at ? makeEvent("completed", "Завершено", row.recommendation ? String(row.recommendation) : "Результат зафиксирован.", "process", row.completed_at) : null,
    ]);
  }

  if (props.businessKind === "protocols") {
    return compactEvents([
      makeEvent("created", "Создано", "Протокол сформирован по завершённым образцам.", "registrar", row.created_at),
      row.issued_at
        ? makeEvent("issued", "Выдано", row.is_signed ? "Протокол подписан и выдан." : "Протокол выдан.", "process", row.issued_at)
        : null,
    ]);
  }

  return [];
});

const statusStepperItems = computed(() => timelineEventsToStepperItems(statusHistory.value, "i-lucide-circle-dot"));
const activeStatusStepIndex = computed(() => getLastStepperIndex(statusStepperItems.value));

const technicalAudit = computed<TimelineEvent[]>(() => {
  const row = currentItem.value;
  if (!row) return [];

  if (auditHistory.value.length) {
    return auditHistory.value.map(historyEntryToTechnicalAuditEvent);
  }

  return compactEvents([
    makeEvent("entity", "Запись создана", `Код записи: ${entityDisplayCode(row.id)}`, "system", row.created_at ?? row.inserted_at ?? null),
    props.businessKind === "research"
      ? makeEvent(
          "recommendation",
          "Текущая рекомендация",
          formatPlain(row.recommendation),
          "api",
          row.updated_at ?? row.modified_at ?? null,
        )
      : null,
    makeEvent("status", "Текущее состояние", statusLabel.value || "Статус не указан", "process", row.completed_at ?? row.updated_at ?? null),
  ]);
});

watch(
  () => [props.open, props.item?.id, props.config.endpoint] as const,
  async ([open]) => {
    if (!open || !props.item?.id) {
      resetState();
      return;
    }

    activeTab.value = "card";
    editing.value = false;
    loading.value = true;
    loadError.value = null;

    try {
      const response = await apiReadRequest<CrudRow>(`${props.config.endpoint}/${props.item.id}`);
      detail.value = { ...props.item, ...response.data };
    } catch (error) {
      detail.value = props.item;
      loadError.value = error instanceof Error ? error.message : "Не удалось загрузить детальную запись";
    } finally {
      syncForm();
      loading.value = false;
      void loadAuditHistory(detail.value);
      void loadRelatedRows(true);
      void loadSelectOptions();
    }
  },
  { immediate: true },
);

function resetState() {
  detail.value = null;
  relatedRows.value = [];
  auditHistory.value = [];
  relatedCursor.value = null;
  relatedHasMore.value = false;
  loadError.value = null;
  editing.value = false;
}

function syncForm() {
  const row = currentItem.value;
  props.config.fields.forEach((field) => {
    const value = row ? getValueByPath(row, field.key) : null;
    formState[field.key] = normalizeFormValue(value);
  });
}

function formString(key: string) {
  const value = formState[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function formBoolean(key: string) {
  return Boolean(formState[key]);
}

function setFormValue(key: string, value: unknown) {
  formState[key] = normalizeFormValue(value);
}

function displayFieldValue(field: { key: string; value: unknown }) {
  const row = currentItem.value;
  if (row && field.key.endsWith("_id")) {
    const relationKey = field.key.replace(/_id$/, "");
    const relationValue = namedValue(row[relationKey]);
    if (relationValue) return relationValue;

    const referenceValue = referenceLabel(field.key, field.value);
    if (referenceValue) return referenceValue;

    const fallbackCode = entityDisplayCode(field.value);
    if (fallbackCode) return fallbackCode;
  }

  return formatDisplay(field.value);
}

function referenceLabel(fieldKey: string, value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "";
  }

  return referenceOptions.value[fieldKey]?.find((option) => String(option.value) === String(value))?.label ?? "";
}

function relationDisplayLabel(row: CrudRow, relationKey: string) {
  return namedValue(row[relationKey]) || referenceLabel(`${relationKey}_id`, row[`${relationKey}_id`]);
}

async function loadSelectOptions() {
  await Promise.all(
    props.config.fields
      .filter((field) => field.type === "select" && field.source && !referenceOptions.value[field.key])
      .map(async (field) => {
        const options = await loadReferenceOptions(field.source as string).catch(() => []);
        referenceOptions.value = {
          ...referenceOptions.value,
          [field.key]: options as Array<{ label: string; value: FieldValue }>,
        };
      }),
  );
}

async function loadAuditHistory(row: CrudRow | null) {
  if (!row?.id || !props.businessKind) {
    auditHistory.value = [];
    return;
  }

  try {
    const response = await apiReadListRequest<TechnicalAuditHistoryEntry>("/history", {
      method: "GET",
      params: {
        limit: 20,
        filters: JSON.stringify({
          entity_type: props.businessKind,
          entity_id: row.id,
        }),
      },
    });
    auditHistory.value = response.items;
  } catch {
    auditHistory.value = [];
  }
}

async function saveInline() {
  const row = currentItem.value;
  if (!row) return;

  saving.value = true;
  try {
    const payload: Record<string, unknown> = Object.fromEntries(
      props.config.fields.map((field) => [field.key, formState[field.key] ?? null]),
    );
    // Протокол — командная сущность: PATCH /protocols/{id} требует actor_id
    // в теле (см. UpdateProtocolRequest), в отличие от плоского CRUD
    // направлений/образцов.
    if (props.businessKind === "protocols" && auth.user?.id) {
      payload.actor_id = auth.user.id;
    }
    const response = await apiUpdateRequest<CrudRow>(`${props.config.endpoint}/${row.id}`, {
      method: "PATCH",
      body: payload,
    });
    detail.value = { ...row, ...payload, ...response.data };
    editing.value = false;
    emit("saved", detail.value);
    await loadAuditHistory(detail.value);
  } finally {
    saving.value = false;
  }
}

async function saveRelatedTests() {
  if (props.businessKind !== "research") return;

  testsSaving.value = true;
  try {
    await Promise.all(
      relatedRows.value.map((row) =>
        apiUpdateRequest<CrudRow>(`/tests/${row.id}`, {
          method: "PATCH",
          body: {
            value: row.value ?? null,
            norm: row.norm ?? null,
            comment: row.comment ?? null,
          },
        }),
      ),
    );
    await loadRelatedRows(true);
  } finally {
    testsSaving.value = false;
  }
}

function close() {
  emit("update:open", false);
}

</script>

<template>
  <UModal
    :open="open"
    :ui="modalUi"
    :dismissible="false"
    @update:open="emit('update:open', $event)"
  >
    <template #content>
      <div v-if="currentItem" class="flex h-full overflow-hidden bg-default">
        <EntityDetailMasterList
          v-if="listItems"
          :items="listItems ?? []"
          :selected-id="selectedId"
          :has-more="listHasMore"
          :loading-more="listLoadingMore"
          @select="emit('select', $event)"
          @load-more="emit('list-load-more')"
        />
        <div class="flex h-full min-w-0 flex-1 flex-col overflow-hidden">
          <header class="border-b border-default px-5 py-4">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div class="flex min-w-0 gap-3">
                <div class="flex size-11 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
                  <UIcon
                    :name="businessKind === 'directions' ? 'i-lucide-clipboard-list' : businessKind === 'samples' ? 'i-lucide-test-tube-2' : businessKind === 'research' ? 'i-lucide-flask-conical' : 'i-lucide-database'"
                    class="size-5"
                  />
                </div>
                <div class="min-w-0">
                  <p class="truncate text-xs font-semibold uppercase tracking-wide text-muted">
                    Карточка · {{ config.title }}
                  </p>
                  <h2 class="mt-1 truncate text-2xl font-semibold text-highlighted">
                    {{ title }}
                  </h2>
                  <p class="mt-1 truncate text-sm text-muted">
                    {{ subtitle }}
                  </p>
                  <div class="mt-3 flex flex-wrap items-center gap-2">
                    <UBadge
                      v-if="statusLabel"
                      :color="statusColor"
                      variant="subtle"
                      :label="statusLabel"
                    />
                    <UBadge
                      :color="currentItem.is_urgent ? 'warning' : 'neutral'"
                      variant="outline"
                      :label="currentItem.is_urgent ? 'Срочно' : 'Normal'"
                    />
                    <UBadge color="neutral" variant="outline" :label="`Код записи ${entityDisplayCode(currentItem.id)}`" />
                    <UBadge
                      v-if="loadError"
                      color="warning"
                      variant="subtle"
                      label="Данные из таблицы"
                    />
                  </div>
                </div>
              </div>

              <div class="flex shrink-0 items-center gap-2">
                <UButton
                  v-if="!editing && businessKind === 'protocols'"
                  label="Предпросмотр"
                  icon="i-lucide-file-search"
                  color="neutral"
                  variant="outline"
                  size="sm"
                  @click="openPreview"
                />
                <UTooltip :text="fullscreen ? 'Обычный размер' : 'На весь экран'">
                  <UButton
                    :icon="fullscreen ? 'i-lucide-minimize-2' : 'i-lucide-maximize-2'"
                    color="neutral"
                    variant="ghost"
                    square
                    @click="fullscreen = !fullscreen"
                  />
                </UTooltip>
                <UButton
                  icon="i-lucide-x"
                  color="neutral"
                  variant="ghost"
                  square
                  @click="close"
                />
              </div>
            </div>
          </header>

          <UTabs
            v-model="activeTab"
            :items="tabs"
            variant="link"
            :content="false"
            class="border-b border-default px-5"
          />

          <main
            class="min-h-0 flex-1 px-5 py-5"
            :class="activeTab === 'related' ? 'overflow-hidden' : 'overflow-auto'"
          >
            <div v-if="loading" class="space-y-3">
              <USkeleton class="h-24 w-full" />
              <USkeleton class="h-64 w-full" />
            </div>

            <div v-else-if="activeTab === 'card'" class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(19rem,25rem)]">
              <section class="min-w-0 space-y-5">
                <div>
                  <div class="mb-3 flex items-center justify-between gap-3">
                    <h3 class="text-sm font-semibold text-highlighted">
                      Данные
                    </h3>
                    <div class="flex gap-2">
                      <UButton
                        v-if="!editing && canEditEntity"
                        label="Редактировать"
                        icon="i-lucide-pencil"
                        color="neutral"
                        variant="outline"
                        size="sm"
                        @click="editing = true"
                      />
                      <template v-else-if="editing">
                        <UButton
                          label="Отменить"
                          color="neutral"
                          variant="outline"
                          size="sm"
                          :disabled="saving"
                          @click="editing = false; syncForm()"
                        />
                        <UButton
                          label="Сохранить"
                          icon="i-lucide-save"
                          color="primary"
                          size="sm"
                          :loading="saving"
                          @click="saveInline"
                        />
                      </template>
                    </div>
                  </div>

                  <div class="overflow-hidden rounded-lg border border-default">
                    <dl class="grid text-sm md:grid-cols-2">
                      <div
                        v-for="field in visibleFields"
                        :key="field.key"
                        class="grid grid-cols-[9.5rem_minmax(0,1fr)] border-b border-default last:border-b-0 md:[&:nth-last-child(-n+2)]:border-b-0 md:odd:border-e"
                      >
                        <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                          {{ field.label }}
                        </dt>
                        <dd class="min-w-0 px-3 py-2 text-muted">
                          <template v-if="editing">
                            <UTextarea
                              v-if="field.type === 'textarea'"
                              :model-value="formString(field.key)"
                              autoresize
                              :rows="2"
                              @update:model-value="setFormValue(field.key, $event)"
                            />
                            <USwitch
                              v-else-if="field.type === 'boolean'"
                              :model-value="formBoolean(field.key)"
                              @update:model-value="setFormValue(field.key, $event)"
                            />
                            <USelectMenu
                              v-else-if="field.type === 'select'"
                              v-model="formState[field.key]"
                              :items="referenceOptions[field.key] || []"
                              value-key="value"
                              label-key="label"
                              class="w-full"
                            />
                            <UInput
                              v-else
                              :model-value="formString(field.key)"
                              :type="field.type === 'number' ? 'number' : 'text'"
                              @update:model-value="setFormValue(field.key, $event)"
                            />
                          </template>
                          <span v-else class="block truncate">
                            {{ displayFieldValue(field) }}
                          </span>
                        </dd>
                      </div>
                    </dl>
                  </div>
                </div>

                <div v-if="isStatusTracked" class="grid gap-3 sm:grid-cols-3">
                  <div class="rounded-lg border border-default bg-elevated/40 p-3">
                    <p class="text-xs text-muted">
                      Поля
                    </p>
                    <p class="mt-1 text-2xl font-semibold text-highlighted">
                      {{ visibleFields.length }}
                    </p>
                  </div>
                  <div class="rounded-lg border border-default bg-elevated/40 p-3">
                    <p class="text-xs text-muted">
                      Связанные
                    </p>
                    <p class="mt-1 text-2xl font-semibold text-highlighted">
                      {{ relatedRows.length }}
                    </p>
                  </div>
                  <div class="rounded-lg border border-default bg-elevated/40 p-3">
                    <p class="text-xs text-muted">
                      Переходы
                    </p>
                    <p class="mt-1 text-2xl font-semibold text-highlighted">
                      {{ statusHistory.length }}
                    </p>
                  </div>
                </div>

                <UAlert
                  v-if="loadError"
                  color="warning"
                  variant="subtle"
                  icon="i-lucide-triangle-alert"
                  title="Backend вернул ошибку при чтении карточки"
                  description="Карточка построена по данным строки таблицы."
                />
              </section>

              <aside class="min-w-0">
                <div class="mb-3 flex items-center justify-between gap-3">
                  <h3 class="text-sm font-semibold text-highlighted">
                    История переходов статуса
                  </h3>
                  <UBadge color="neutral" variant="outline" :label="`${statusHistory.length} события`" />
                </div>

                <UStepper
                  v-if="statusStepperItems.length"
                  orientation="vertical"
                  :items="statusStepperItems"
                  :model-value="activeStatusStepIndex"
                  disabled
                  class="w-full"
                  :ui="timelineStepperUi"
                >
                  <template #description="{ item: stepperItem }">
                    <div class="space-y-1">
                      <p class="whitespace-pre-line break-words text-xs leading-5 text-muted">
                        {{ stepperItem.description }}
                      </p>
                      <div class="flex flex-wrap items-center gap-2">
                        <UBadge
                          v-if="stepperItem.actor"
                          color="neutral"
                          variant="outline"
                          size="sm"
                          :label="stepperItem.actor"
                        />
                        <p class="font-mono text-xs text-muted">
                          {{ stepperItem.date ? formatDateTime(stepperItem.date) : 'Дата не указана' }}
                        </p>
                      </div>
                    </div>
                  </template>
                </UStepper>
              </aside>
            </div>

            <TechnicalAuditTimeline
              v-else-if="activeTab === 'technical'"
              :events="technicalAudit"
            />

            <EntityRelatedTab
              v-else-if="activeTab === 'related'"
              :business-kind="businessKind"
              :rows="relatedRows"
              :loading="relatedLoading"
              :loading-more="relatedLoadingMore"
              :has-more="relatedHasMore"
              :tests-saving="testsSaving"
              :can-add-sample="canAddSampleToDirection"
              @load-more="loadRelatedRows(false)"
              @save-tests="saveRelatedTests"
              @open-related="emit('open-related', $event)"
              @add-sample="openAddSample"
            />
          </main>

          <footer class="flex flex-col gap-3 border-t border-default bg-elevated/40 px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div class="flex items-center gap-2 text-xs text-muted">
              <UIcon name="i-lucide-lock" class="size-4" />
              <span>Статус меняется только через процесс</span>
            </div>
            <div class="flex justify-end gap-2">
              <UButton
                label="Закрыть"
                color="neutral"
                variant="outline"
                @click="close"
              />
            </div>
          </footer>
        </div>
      </div>
    </template>
  </UModal>

  <CrudFormModal
    v-model:open="addSampleOpen"
    title="Добавить образец в направление"
    :fields="sampleCreateFields"
    :item="null"
    mode="create"
    :loading="addSampleSaving"
    @save="saveNewSample"
  />

  <ProtocolPreviewModal
    v-if="businessKind === 'protocols'"
    v-model:open="previewOpen"
    :protocol="currentItem"
    :samples="relatedRows"
  />
</template>
