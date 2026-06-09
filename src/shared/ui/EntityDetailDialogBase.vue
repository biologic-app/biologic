<script setup lang="ts">
import { computed, h, reactive, ref, resolveComponent, watch } from "vue";
import type { TableColumn, TabsItem } from "@nuxt/ui";
import type { CrudModuleConfig } from "@/pages/CrudModulePage.vue";
import {
  apiReadListRequest,
  apiReadRequest,
  apiUpdateRequest,
  loadReferenceOptions,
} from "@/shared/api/client.api";
import TechnicalAuditTimeline from "@/shared/ui/TechnicalAuditTimeline.vue";
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

type EntityKind = "directions" | "samples" | "research";

type CrudRow = {
  id: string | number;
  [key: string]: unknown;
};

type FieldValue = string | number | boolean | null;
const RELATED_PAGE_SIZE = 20;

interface TimelineEvent {
  id: string;
  label: string;
  description: string;
  actor: string;
  date?: string | null;
}

interface RelatedRow extends CrudRow {
  relationKind: EntityKind | "tests";
  type: string;
  title: string;
  statusText: string;
  updatedAtText: string;
}

const props = defineProps<{
  open: boolean;
  config: CrudModuleConfig;
  item: CrudRow | null;
  businessKind?: EntityKind | null;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
  (event: "open-related", payload: { kind: EntityKind; item: CrudRow }): void;
}>();

const UBadge = resolveComponent("UBadge");
const activeTab = ref<"card" | "technical" | "related" | "notes">("card");
const detail = ref<CrudRow | null>(null);
const relatedRows = ref<RelatedRow[]>([]);
const auditHistory = ref<TechnicalAuditHistoryEntry[]>([]);
const loading = ref(false);
const relatedLoading = ref(false);
const relatedLoadingMore = ref(false);
const relatedCursor = ref<string | null>(null);
const relatedHasMore = ref(false);
const saving = ref(false);
const testsSaving = ref(false);
const editing = ref(false);
const fullscreen = ref(false);
const loadError = ref<string | null>(null);
const note = ref("");
const formState = reactive<Record<string, FieldValue>>({});
const referenceOptions = ref<Record<string, Array<{ label: string; value: FieldValue }>>>({});

const currentItem = computed(() => detail.value ?? props.item);
const isStatusTracked = computed(() => Boolean(props.businessKind));

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
  { label: "Заметки", icon: "i-lucide-message-square", value: "notes" },
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

const relatedTitle = computed(() => {
  if (props.businessKind === "directions") return "Образцы направления";
  if (props.businessKind === "samples") return "Исследования образца";
  if (props.businessKind === "research") return "Тесты исследования";
  return "Связанные элементы";
});

const relatedColumns = computed<TableColumn<RelatedRow>[]>(() => {
  const base: TableColumn<RelatedRow>[] = [
    { accessorKey: "type", header: "Тип" },
    { accessorKey: "title", header: "Название" },
    {
      accessorKey: "statusText",
      header: "Статус",
      cell: ({ row }) => h(UBadge, {
        color: row.original.statusText === "-" ? "neutral" : "primary",
        variant: "subtle",
        label: row.original.statusText,
      }),
    },
    { accessorKey: "updatedAtText", header: "Обновлено" },
  ];

  if (props.businessKind === "research") {
    return [
      ...base,
      {
        accessorKey: "value",
        header: "Значение",
        cell: ({ row }) => formatPlain(row.original.value),
      },
      {
        accessorKey: "norm",
        header: "Норма",
        cell: ({ row }) => formatPlain(row.original.norm),
      },
    ];
  }

  return [
    ...base,
    {
      id: "actions",
      header: "",
      cell: ({ row }) => h("div", { class: "flex justify-end gap-1" }, [
        h(resolveComponent("UButton"), {
          icon: "i-lucide-panel-top-open",
          color: "neutral",
          variant: "ghost",
          size: "sm",
          "aria-label": "Открыть карточку",
          onClick: () => openRelated(row.original),
        }),
        h(resolveComponent("UButton"), {
          icon: "i-lucide-arrow-up-right",
          color: "neutral",
          variant: "ghost",
          size: "sm",
          to: routeForRelated(row.original.relationKind),
          "aria-label": "Перейти на страницу",
        }),
      ]),
    },
  ];
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

function normalizeFormValue(value: unknown): FieldValue {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }

  if (value === null || value === undefined) {
    return null;
  }

  return String(value);
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

function entityDisplayCode(value: unknown) {
  if (typeof value !== "string" && typeof value !== "number") {
    return "";
  }

  const text = String(value);
  const uuidPrefix = text.match(/^[0-9a-f]{8}/i)?.[0];
  return `#${(uuidPrefix ?? text.slice(0, 8)).toUpperCase()}`;
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

async function loadRelatedRows(reset = false) {
  const row = currentItem.value;
  const relation = relationRequest(row);
  if (!row || !relation) {
    relatedRows.value = [];
    relatedCursor.value = null;
    relatedHasMore.value = false;
    return;
  }

  if (reset) {
    relatedRows.value = [];
    relatedCursor.value = null;
    relatedHasMore.value = false;
    relatedLoading.value = true;
  } else {
    relatedLoadingMore.value = true;
  }

  try {
    const response = await apiReadListRequest<CrudRow>(relation.endpoint, {
      method: "GET",
      params: {
        limit: RELATED_PAGE_SIZE,
        cursor: reset ? undefined : relatedCursor.value,
        include: relation.include,
        filters: JSON.stringify({ [relation.filterKey]: row.id }),
      },
    });
    const nextRows = response.items.map((item) => normalizeRelatedRow(item, relation.kind));
    relatedRows.value = reset ? nextRows : [...relatedRows.value, ...nextRows];
    relatedCursor.value = response.meta.nextCursor ?? null;
    relatedHasMore.value = Boolean(response.meta.hasMore ?? response.meta.nextCursor);
  } catch {
    if (reset) {
      relatedRows.value = [];
      relatedCursor.value = null;
      relatedHasMore.value = false;
    }
  } finally {
    relatedLoading.value = false;
    relatedLoadingMore.value = false;
  }
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

function relationRequest(row: CrudRow | null) {
  if (!row) return null;

  if (props.businessKind === "directions") {
    return {
      endpoint: "/samples",
      include: "sample_type,status,direction,protocol",
      filterKey: "direction_id",
      kind: "samples" as const,
    };
  }

  if (props.businessKind === "samples") {
    return {
      endpoint: "/research",
      include: "sample,research_goal,lab,status",
      filterKey: "sample_id",
      kind: "research" as const,
    };
  }

  if (props.businessKind === "research") {
    return {
      endpoint: "/tests",
      include: "research,indicator,status",
      filterKey: "research_id",
      kind: "tests" as const,
    };
  }

  return null;
}

function normalizeRelatedRow(row: CrudRow, kind: EntityKind | "tests"): RelatedRow {
  return {
    ...row,
    relationKind: kind,
    type: relationLabel(kind),
    title: pickText(row, ["name", "indicator.name", "research_goal.name", "sample.name", "code"]),
    statusText: namedValue(row.status) || booleanStatus(row) || "-",
    updatedAtText: formatDisplay(row.updated_at ?? row.completed_at ?? row.received_at),
  };
}

async function saveInline() {
  const row = currentItem.value;
  if (!row) return;

  saving.value = true;
  try {
    const payload = Object.fromEntries(
      props.config.fields.map((field) => [field.key, formState[field.key] ?? null]),
    );
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

function relatedString(row: RelatedRow, key: string) {
  const value = row[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function setRelatedValue(row: RelatedRow, key: string, value: unknown) {
  row[key] = normalizeFormValue(value);
}

function openRelated(row: RelatedRow) {
  if (row.relationKind === "tests") return;
  emit("open-related", { kind: row.relationKind, item: row });
}

function routeForRelated(kind: EntityKind | "tests") {
  if (kind === "samples") return "/samples";
  if (kind === "research") return "/research";
  if (kind === "directions") return "/directions";
  return "/dictionaries/tests";
}

function close() {
  emit("update:open", false);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function compact<T>(items: Array<T | null | undefined | false | "">): T[] {
  return items.filter(Boolean) as T[];
}

function compactEvents(items: Array<TimelineEvent | null>): TimelineEvent[] {
  return items.filter(Boolean) as TimelineEvent[];
}

function namedValue(value: unknown): string {
  if (isRecord(value)) {
    return formatPlain(value.name ?? value.full_name ?? value.code ?? value.id);
  }

  return "";
}

function booleanStatus(row: CrudRow) {
  if (typeof row.is_done === "boolean") {
    return row.is_done ? "Завершено" : "В работе";
  }

  return "";
}

function pickText(row: CrudRow, paths: string[]) {
  for (const path of paths) {
    const value = getValueByPath(row, path);
    const text = formatPlain(value);
    if (text !== "-") return text;
  }

  return "";
}

function formatPlain(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (isRecord(value)) return namedValue(value) || JSON.stringify(value);
  return String(value);
}

function formatDisplay(value: unknown): string {
  if (typeof value === "string" && /(T|\d{4}-\d{2}-\d{2})/.test(value)) {
    return formatDateTime(value);
  }

  return formatPlain(value);
}

function makeEvent(
  id: string,
  label: string,
  description: string,
  actor: string,
  date: unknown,
): TimelineEvent {
  return {
    id,
    label,
    description,
    actor: actor || "system",
    date: typeof date === "string" ? date : null,
  };
}

function relationLabel(kind: EntityKind | "tests") {
  const labels: Record<EntityKind | "tests", string> = {
    directions: "Направление",
    samples: "Образец",
    research: "Исследование",
    tests: "Тест",
  };

  return labels[kind];
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
      <div v-if="currentItem" class="flex h-full flex-col overflow-hidden bg-default">
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

            <div class="flex shrink-0 items-center gap-1">
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
                      v-if="!editing"
                      label="Редактировать"
                      icon="i-lucide-pencil"
                      color="neutral"
                      variant="outline"
                      size="sm"
                      @click="editing = true"
                    />
                    <template v-else>
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

          <section v-else-if="activeTab === 'related'" class="flex h-full min-h-0 flex-col gap-3">
            <div class="flex shrink-0 items-center justify-between gap-3">
              <h3 class="text-sm font-semibold text-highlighted">
                {{ relatedTitle }}
              </h3>
              <div class="flex items-center gap-2">
                <UBadge color="neutral" variant="outline" :label="`${relatedRows.length} записей`" />
                <UButton
                  v-if="businessKind === 'research' && relatedRows.length"
                  label="Сохранить тесты"
                  icon="i-lucide-save"
                  size="sm"
                  color="primary"
                  :loading="testsSaving"
                  @click="saveRelatedTests"
                />
              </div>
            </div>

            <div
              v-if="businessKind === 'research'"
              class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-default"
            >
              <div class="min-h-0 flex-1 overflow-auto">
                <table class="w-full min-w-[900px] border-collapse text-sm">
                  <thead class="sticky top-0 z-10 bg-elevated text-left text-xs font-medium uppercase text-muted">
                    <tr>
                      <th class="border-b border-default px-3 py-2">
                        Показатель
                      </th>
                      <th class="border-b border-default px-3 py-2">
                        Статус
                      </th>
                      <th class="border-b border-default px-3 py-2">
                        Значение
                      </th>
                      <th class="border-b border-default px-3 py-2">
                        Норма
                      </th>
                      <th class="border-b border-default px-3 py-2">
                        Комментарий
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="row in relatedRows"
                      :key="row.id"
                      class="border-b border-default last:border-b-0"
                    >
                      <td class="px-3 py-2 align-top">
                        <p class="font-medium text-highlighted">
                          {{ row.title }}
                        </p>
                      </td>
                      <td class="px-3 py-2 align-top">
                        <UBadge color="primary" variant="subtle" :label="row.statusText" />
                      </td>
                      <td class="px-3 py-2 align-top">
                        <UInput
                          :model-value="relatedString(row, 'value')"
                          @update:model-value="setRelatedValue(row, 'value', $event)"
                        />
                      </td>
                      <td class="px-3 py-2 align-top">
                        <UInput
                          :model-value="relatedString(row, 'norm')"
                          @update:model-value="setRelatedValue(row, 'norm', $event)"
                        />
                      </td>
                      <td class="px-3 py-2 align-top">
                        <UTextarea
                          :model-value="relatedString(row, 'comment')"
                          autoresize
                          :rows="1"
                          @update:model-value="setRelatedValue(row, 'comment', $event)"
                        />
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div v-if="!relatedLoading && !relatedRows.length" class="px-4 py-8 text-center text-sm text-muted">
                  Связанные элементы не найдены.
                </div>
              </div>
              <div v-if="relatedHasMore" class="shrink-0 border-t border-default px-3 py-2 text-center">
                <UButton
                  label="Загрузить ещё"
                  color="neutral"
                  variant="outline"
                  size="sm"
                  :loading="relatedLoadingMore"
                  @click="loadRelatedRows(false)"
                />
              </div>
            </div>

            <div v-else class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-default">
              <div class="min-h-0 flex-1 overflow-auto">
                <UTable
                  :data="relatedRows"
                  :columns="relatedColumns"
                  :loading="relatedLoading"
                  :ui="{ thead: 'sticky top-0 z-10 bg-elevated', th: 'px-4 py-2 text-left text-sm font-semibold text-highlighted', td: 'px-4 py-2 align-middle text-sm text-muted whitespace-nowrap' }"
                />
                <div v-if="!relatedLoading && !relatedRows.length" class="px-4 py-8 text-center text-sm text-muted">
                  Связанные элементы не найдены.
                </div>
              </div>
              <div v-if="relatedHasMore" class="shrink-0 border-t border-default px-3 py-2 text-center">
                <UButton
                  label="Загрузить ещё"
                  color="neutral"
                  variant="outline"
                  size="sm"
                  :loading="relatedLoadingMore"
                  @click="loadRelatedRows(false)"
                />
              </div>
            </div>
          </section>

          <section v-else class="space-y-4">
            <div class="space-y-3 border-b border-default pb-4">
              <div>
                <p class="text-sm text-highlighted">
                  Внутренний комментарий
                </p>
                <p class="text-xs text-muted">
                  Заметки не меняют статус.
                </p>
              </div>
              <UTextarea
                v-model="note"
                autoresize
                :rows="4"
                placeholder="Добавьте внутренний комментарий"
              />
            </div>
          </section>
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
    </template>
  </UModal>
</template>
