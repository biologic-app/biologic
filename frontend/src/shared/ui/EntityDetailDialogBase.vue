<script setup lang="ts">
import { computed, defineAsyncComponent, ref, resolveComponent, watch } from "vue";
import type { DropdownMenuItem, TabsItem, TimelineItem } from "@nuxt/ui";
import type { CrudModuleConfig } from '@/shared/types/crud';
import {
  apiCommandRequest,
  apiCreateRequest,
  apiReadListRequest,
  apiReadRequest,
  apiUpdateRequest,
  buildApiUrl,
  loadReferenceOptions,
} from "@/shared/api/client.api";
import { usePermission } from "@/shared/composables/usePermission";
import { useAuth } from "@/modules/auth";
import { useEntityForm } from "@/shared/composables/useEntityForm";
import ProtocolPreviewModal from "@/shared/ui/ProtocolPreviewModal.vue";
import TechnicalAuditTimeline from "@/shared/ui/TechnicalAuditTimeline.vue";
import EntityRelatedTab from "@/shared/ui/EntityRelatedTab.vue";
// Ленивая загрузка: вкладка с воркфлоу-журналом нужна только в Исследованиях V2,
// не тянем модуль journals в чанк карточки для остальных сущностей.
const ResearchWorkflowTab = defineAsyncComponent(
  () => import("@/modules/journals/components/ResearchWorkflowTab.vue"),
);
import EntityDetailModalShell from "@/shared/ui/EntityDetailModalShell.vue";
import type { DetailListItem } from "@/shared/ui/EntityDetailMasterList.vue";
import EntityFieldGrid, { type GridField } from "@/shared/ui/EntityFieldGrid.vue";
import { buildFallbackAuditEvents } from "@/shared/ui/entity-technical-audit";
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
  isSampleDeadlineOverdue,
  makeEvent,
  namedValue,
  pickText,
  recordCode,
  type DetailTimelineEvent,
  type EntityKind,
  type RelatedRow,
} from "@/shared/ui/entity-detail.helpers";
import { useRelatedEntities } from "@/shared/composables/useRelatedEntities";
import SubscribeButton from "@/shared/ui/SubscribeButton.vue";
import {
  DIRECTION_STATUS_FLOW,
  SAMPLE_STATUS_FLOW,
  SAMPLE_STATUS_REJECTED,
  statusTimelineItems,
} from "@/shared/domain/status-timeline";

type CrudRow = {
  id: string | number;
  [key: string]: unknown;
};

type FieldValue = string | number | boolean | null;
type TimelineEvent = DetailTimelineEvent;

const props = withDefaults(
  defineProps<{
    open: boolean;
    config: CrudModuleConfig;
    item: CrudRow | null;
    businessKind?: EntityKind | null;
    listItems?: DetailListItem[];
    listLabel?: string;
    selectedId?: string | number | null;
    listHasMore?: boolean;
    listLoadingMore?: boolean;
    // "create" открывает карточку как форму создания новой записи (без чтения
    // с бэкенда, сразу в editing), "view" — обычный просмотр существующей.
    mode?: "view" | "create";
    // Открыть карточку существующей записи сразу в режиме редактирования
    // (точка входа "Редактировать" из таблицы).
    startInEdit?: boolean;
    // Предзаполненные значения полей для create-режима (например direction_id
    // при создании образца из карточки родительского направления).
    initialValues?: Record<string, unknown> | null;
    // Хлебные крошки стека открытых карточек (см. DictionaryCrudContent).
    // Показываются всегда, когда карточка открыта (даже одна крошка).
    breadcrumbs?: Array<{ label: string }>;
    // Действия строки (переходы статуса, удаление, мастер импорта), которые
    // раньше были доступны только из меню строки таблицы. Приходят готовыми
    // пунктами от родителя (DictionaryCrudContent) и рендерятся кнопками в
    // шапке карточки. Пустой массив — кнопки не показываем.
    headerActions?: DropdownMenuItem[];
    // Инкремент этого счётчика заставляет карточку перечитать запись с бэкенда
    // (после команды воркфлоу из шапки статус меняется — нужно обновить данные).
    reloadToken?: number;
    // Исследования V2: вместо таба «Тесты» показывать вкладку «Рабочий процесс»
    // (пошаговый воркфлоу-журнал, привязанный к исследованию).
    researchWorkflow?: boolean;
  }>(),
  {
    businessKind: null,
    listItems: undefined,
    listLabel: "",
    selectedId: null,
    listHasMore: false,
    listLoadingMore: false,
    mode: "view",
    startInEdit: false,
    initialValues: null,
    breadcrumbs: () => [],
    headerActions: () => [],
    reloadToken: 0,
    researchWorkflow: false,
  },
);

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
  (event: "open-related", payload: { kind: EntityKind; item: CrudRow; parent?: { kind: EntityKind; item: CrudRow } }): void;
  (event: "create-related", payload: { kind: EntityKind }): void;
  (event: "go-to-level", index: number): void;
  (event: "select", id: string | number): void;
  (event: "list-load-more"): void;
}>();

const UBadge = resolveComponent("UBadge");
const activeTab = ref<string>("card");
const detail = ref<CrudRow | null>(null);
const auditHistory = ref<TechnicalAuditHistoryEntry[]>([]);
const loading = ref(false);
const saving = ref(false);
const testsSaving = ref(false);
const editing = ref(false);
const loadError = ref<string | null>(null);
const referenceOptions = ref<Record<string, Array<{ label: string; value: FieldValue }>>>({});
const previewOpen = ref(false);

const { can } = usePermission();
const auth = useAuth();
const toast = useToast();
const { formState, sync, setValue, buildPayload, missingRequired } = useEntityForm();

// Режим определяется внутренне: после успешного создания карточка сама
// переключается в "view" на только что созданную запись (prop mode неизменен).
const internalMode = ref<"view" | "create">("view");
const isCreate = computed(() => internalMode.value === "create");

const currentItem = computed<CrudRow | null>(() => {
  if (isCreate.value) return detail.value ?? ({ id: "" } as CrudRow);
  return detail.value ?? props.item;
});

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
    !isCreate.value
    && props.businessKind === "directions"
    && statusCode === "draft"
    && can("samples", "create")
  );
});

async function openPreview() {
  if (!relatedRows.value.length) {
    await loadRelatedRows(true);
  }
  previewOpen.value = true;
}

// Скачивание XLS протокола: `document` — полный документ по всем образцам,
// `excerpt` — выписка только по образцам в статусе «Брак». Оба эндпоинта отдают
// бинарный файл (не JSON), поэтому идём напрямую через fetch мимо типизированного
// SDK-клиента; базовый URL и куки авторизации берём тем же механизмом
// (buildApiUrl + credentials: 'include'), что и остальные запросы.
const downloadingKind = ref<"document" | "excerpt" | null>(null);

async function downloadProtocolFile(kind: "document" | "excerpt") {
  const id = currentItem.value?.id;
  if (!id) return;

  const errorTitle =
    kind === "document" ? "Не удалось скачать документ" : "Не удалось сформировать выписку";
  downloadingKind.value = kind;
  try {
    const res = await fetch(buildApiUrl(`/protocols/${id}/${kind}`), {
      credentials: "include",
    });
    if (!res.ok) {
      toast.add({ title: errorTitle, color: "error", icon: "i-lucide-circle-alert" });
      return;
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = /filename="?([^"]+)"?/.exec(disposition);
    const filename = match?.[1] || `protocol-${kind}.xlsx`;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  } catch {
    toast.add({ title: errorTitle, color: "error", icon: "i-lucide-circle-alert" });
  } finally {
    downloadingKind.value = null;
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

const tabs = computed<TabsItem[]>(() => {
  const cardTab = { label: "Карточка", icon: "i-lucide-panel-top", value: "card" as const };
  // У новой записи ещё нет истории/аудита/связанных — оставляем только карточку.
  if (isCreate.value) return [cardTab];
  // «Технический аудит» — не в списке: он рендерится отдельной иконкой,
  // прижатой к правому краю строки вкладок.
  const relatedLabels: Partial<Record<string, { label: string; icon: string }>> = {
    directions: { label: "Образцы", icon: "i-lucide-test-tube-2" },
    samples: { label: "Исследования", icon: "i-lucide-flask-conical" },
    research: { label: "Тесты", icon: "i-lucide-list-checks" },
  };
  // Исследования V2: заменяем таб «Тесты» на вкладку «Рабочий процесс».
  if (props.researchWorkflow && props.businessKind === "research") {
    return [
      cardTab,
      { label: "Рабочий процесс", icon: "i-lucide-workflow", value: "workflow" as const },
    ];
  }
  const related = (props.businessKind && relatedLabels[props.businessKind])
    || { label: "Связанные", icon: "i-lucide-link" };
  return [
    cardTab,
    { label: related.label, icon: related.icon, value: "related", badge: relatedRows.value.length },
  ];
});

const title = computed(() => {
  if (isCreate.value) return "Новая запись";
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

// Заголовок карточки: для направления — код записи (номер, 9 цифр с
// незначащими нулями); для остальных — обычный title.
const headerTitle = computed(() => {
  const row = currentItem.value;
  if (!isCreate.value && row && props.businessKind === "directions") {
    return recordCode(row);
  }
  return title.value;
});

const eyebrowText = computed(
  () => `${isCreate.value ? "Создание" : "Карточка"} · ${props.config.title}`,
);

const subtitle = computed(() => {
  const row = currentItem.value;
  if (!row) return "";

  if (props.businessKind === "directions") {
    // Год и номер уже в заголовке («№ 2025-461»); показываем дату, врача и объект.
    const sampledAt = row.sampled_at ?? row.received_at;
    return compact([
      sampledAt
        ? new Date(String(sampledAt)).toLocaleDateString("ru-RU", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        })
        : null,
      namedValue(row.doctor),
      namedValue(row.object),
    ]).join(" · ") || props.config.description;
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

const gridFields = computed<GridField[]>(() =>
  visibleFields.value.map((field) => ({
    key: field.key,
    label: field.label,
    type: field.type === "file" ? "text" : field.type,
    required: field.required,
    editable: field.editable,
    options: field.options,
    value: field.value,
  })),
);

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

// Код статуса из связанного справочника (status.code) — авторитет для таймлайна.
const statusCode = computed(() => {
  const status = currentItem.value?.status;
  return status && typeof status === "object"
    ? ((status as { code?: string | null }).code ?? null)
    : null;
});

// Цепочка статусов из таблиц direction_statuses / sample_statuses — только они.
const statusFlow = computed(() => {
  if (props.businessKind === "directions") return DIRECTION_STATUS_FLOW;
  if (props.businessKind === "samples") return SAMPLE_STATUS_FLOW;
  return null;
});

// Даты и авторы переходов из change_log: записи с diff.status_code.to —
// это фактические переводы статуса (actor_name резолвится бэкендом в /history).
const statusTransitions = computed(() => {
  const datesByCode: Record<string, string> = {};
  const actorsByCode: Record<string, string> = {};
  // /history отсортирован от новых к старым; идём с конца, чтобы при повторных
  // переходах (reopen/requeue) остался самый свежий.
  for (const entry of [...auditHistory.value].reverse()) {
    const diff = entry.diff as { status_code?: { to?: unknown } } | null | undefined;
    const to = diff?.status_code?.to;
    if (typeof to !== "string") continue;
    if (entry.created_at) datesByCode[to] = formatDateTime(entry.created_at);
    if (entry.actor_name) actorsByCode[to] = entry.actor_name;
  }

  // Первый шаг флоу (draft у направления, pending у образца) в change_log не
  // фиксируется — заполняем его из полей самой записи: дата создания и
  // резолвленный создатель (backend отдаёт `creator` как {last_name,...}).
  const row = currentItem.value;
  const firstCode = statusFlow.value?.[0]?.code;
  if (firstCode && !datesByCode[firstCode] && row?.created_at) {
    datesByCode[firstCode] = formatDateTime(String(row.created_at));
  }
  if (firstCode && !actorsByCode[firstCode]) {
    const creatorName = namedValue(row?.creator ?? row?.created_by);
    if (creatorName) actorsByCode[firstCode] = creatorName;
  }

  return { datesByCode, actorsByCode };
});

// Таймлайн статусов: для образца — от отбора до дедлайна выпуска; на каждой
// достигнутой точке — дата перехода и «Фамилия И.О.» того, кто его выполнил.
// Ведущий этап «Сбор и формирование»: проставляется в направлении при импорте
// (дата отбора + ФИО санитарного врача). Показывается и у образца — сбор
// наследуется от родительского направления. Всегда «пройден» (до первого статуса).
const collectionLeadItem = computed<TimelineItem | null>(() => {
  const row = currentItem.value;
  if (!row) return null;
  const collectedAt = row.sampled_at ?? row.received_at ?? null;
  const doctorName =
    namedValue(row.doctor)
    || namedValue((row.direction as Record<string, unknown> | undefined)?.doctor);
  return {
    value: "collection",
    title: "Сформировано",
    icon: "i-lucide-clipboard-pen",
    description: doctorName || undefined,
    date: collectedAt ? formatDateTime(String(collectedAt)) : undefined,
  };
});

// Русская форма слова «образец» по числу задержавшихся: 1 образец, 2 образца,
// 5 образцов (падежи по последней цифре, кроме 11–14).
const pluralizeSamples = (count: number): string => {
  const mod100 = count % 100;
  const mod10 = count % 10;
  if (mod100 >= 11 && mod100 <= 14) return "образцов";
  if (mod10 === 1) return "образец";
  if (mod10 >= 2 && mod10 <= 4) return "образца";
  return "образцов";
};

// Провал дедлайна выпуска. Образец: свой deadline против completed_at (или
// «сейчас», если ещё не выпущен). Направление: агрегат по образцам — провалено,
// если хоть один задерживается, с указанием количества задержавшихся образцов.
const deadlineStatus = computed<
  { failed: boolean; deadlineLabel: string; description: string } | null
>(() => {
  const row = currentItem.value;
  if (!row) return null;

  if (props.businessKind === "samples") {
    const deadlineRaw = row.deadline;
    if (!deadlineRaw) return null;
    const deadline = new Date(String(deadlineRaw)).getTime();
    if (!Number.isFinite(deadline)) return null;
    const releaseRaw = row.completed_at;
    const release = releaseRaw ? new Date(String(releaseRaw)).getTime() : Date.now();
    const failed = release > deadline;
    return {
      failed,
      deadlineLabel: `Дедлайн: ${formatDateTime(String(deadlineRaw))}`,
      description: failed
        ? releaseRaw
          ? "Выпуск позже дедлайна."
          : "Выпуск задерживается."
        : releaseRaw
          ? "Выпущен в срок."
          : "В пределах срока.",
    };
  }

  if (props.businessKind === "directions") {
    const withDeadline = relatedRows.value
      .map((sample) => ({
        sample,
        deadline: sample.deadline ? new Date(String(sample.deadline)).getTime() : Number.NaN,
      }))
      .filter((entry) => Number.isFinite(entry.deadline));
    if (!withDeadline.length) return null;
    // «Брак» — терминальный статус: такой образец не выпускается и не считается
    // задержанным (та же логика, что в isSampleDeadlineOverdue для таблиц/списка).
    const late = withDeadline.filter(({ sample }) => isSampleDeadlineOverdue(sample));
    const maxDeadline = Math.max(...withDeadline.map((entry) => entry.deadline));
    return {
      failed: late.length > 0,
      deadlineLabel: `Выпуск первого образца: ${formatDateTime(new Date(maxDeadline).toISOString())}`,
      description: late.length
        ? `Задерживается ${late.length} ${pluralizeSamples(late.length)} из ${withDeadline.length}.`
        : "Все образцы в пределах срока.",
    };
  }

  return null;
});

// Замыкающий индикатор дедлайна: серый (не активен) в пределах срока, красный
// при провале. У образца в статусе «Брак» выпуска не будет — индикатор скрыт.
const deadlineTrailItem = computed<TimelineItem | null>(() => {
  if (statusCode.value === SAMPLE_STATUS_REJECTED.code) return null;
  const info = deadlineStatus.value;
  if (!info) return null;
  const item: TimelineItem = {
    value: "deadline",
    title: info.failed ? "Выпуск задержан" : "Дедлайн выпуска",
    icon: info.failed ? "i-lucide-alarm-clock-off" : "i-lucide-alarm-clock",
    description: info.description,
    date: info.deadlineLabel,
  };
  if (info.failed) {
    item.ui = {
      indicator: "bg-error text-inverted ring-2 ring-error/30",
      title: "text-error font-semibold",
      description: "text-error/80",
    };
  }
  return item;
});

const statusTimeline = computed<TimelineItem[]>(() => {
  const row = currentItem.value;
  if (!row || !statusFlow.value || !statusCode.value) return [];
  const start = row.sampled_at ?? row.received_at ?? row.created_at;
  const end = row.deadline ?? row.completed_at;
  const statusItems = statusTimelineItems(statusFlow.value, statusCode.value, {
    startDate: start ? `Отбор: ${formatDateTime(String(start))}` : null,
    endDate: end
      ? `${row.deadline ? "Дедлайн" : "Завершено"}: ${formatDateTime(String(end))}`
      : null,
    datesByCode: statusTransitions.value.datesByCode,
    actorsByCode: statusTransitions.value.actorsByCode,
  });
  return [
    ...(collectionLeadItem.value ? [collectionLeadItem.value] : []),
    ...statusItems,
    ...(deadlineTrailItem.value ? [deadlineTrailItem.value] : []),
  ];
});

// Подписки есть только у направлений и образцов.
const subscriptionEntity = computed(() =>
  props.businessKind === "directions" || props.businessKind === "samples"
    ? props.businessKind
    : null,
);

const technicalAudit = computed<TimelineEvent[]>(() => {
  const row = currentItem.value;
  if (!row) return [];

  if (auditHistory.value.length) {
    return auditHistory.value.map(historyEntryToTechnicalAuditEvent);
  }

  return buildFallbackAuditEvents(row, {
    stateLabel: statusLabel.value,
    savedDescription: "Изменения сохранены через API.",
    extra: props.businessKind === "research"
      ? [makeEvent("recommendation", "Текущая рекомендация", formatPlain(row.recommendation), "api", row.updated_at ?? row.modified_at ?? null)]
      : [],
  });
});

watch(
  () => [props.open, props.item?.id, props.config.endpoint, props.mode, props.startInEdit, props.reloadToken] as const,
  async ([open, , , mode]) => {
    if (!open) {
      resetState();
      return;
    }

    if (mode === "create") {
      internalMode.value = "create";
      activeTab.value = "card";
      detail.value = null;
      auditHistory.value = [];
      relatedRows.value = [];
      loadError.value = null;
      loading.value = false;
      editing.value = true;
      syncForm();
      void loadSelectOptions();
      return;
    }

    internalMode.value = "view";

    if (!props.item?.id) {
      resetState();
      return;
    }

    activeTab.value = "card";
    editing.value = Boolean(props.startInEdit);
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
  internalMode.value = "view";
}

function syncForm() {
  sync(props.config.fields, currentItem.value, isCreate.value ? props.initialValues : null);
}

function displayFieldValue(field: { key: string; value?: unknown }) {
  const row = currentItem.value;
  if (row && field.key.endsWith("_id")) {
    const relationKey = field.key.replace(/_id$/, "");
    const relationValue = namedValue(row[relationKey]);
    if (relationValue) return relationValue;

    const referenceValue = referenceLabel(field.key, field.value);
    if (referenceValue) return referenceValue;

    // Сырые ID в интерфейсе не показываем: если название не нашлось — прочерк.
    return field.value ? "—" : formatDisplay(field.value);
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

function validateRequiredFields(): boolean {
  const missing = missingRequired(props.config.fields);
  if (missing.length) {
    const missingKeys = new Set(missing.map((field) => field.key));
    toast.add({
      title: "Заполните обязательные поля",
      description: props.config.fields
        .filter((field) => missingKeys.has(field.key))
        .map((field) => field.label)
        .join(", "),
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return false;
  }
  return true;
}

function cancelEdit() {
  // В режиме создания отмена = закрытие модалки (пустая read-only карточка
  // без записи не имеет смысла).
  if (isCreate.value) {
    close();
    return;
  }
  editing.value = false;
  syncForm();
}

async function saveCreate() {
  if (!validateRequiredFields()) return;

  saving.value = true;
  try {
    const payload = buildPayload(props.config.fields);
    // Образцы больше не создаются напрямую (POST /samples удалён) — только
    // вложенно в направление: POST /directions/{direction_id}/samples,
    // direction_id берётся из пути, поэтому убираем его из тела.
    let endpoint = props.config.endpoint;
    if (props.businessKind === "samples" && payload.direction_id) {
      endpoint = `/directions/${payload.direction_id}/samples`;
      delete payload.direction_id;
    }
    const response = await apiCreateRequest<CrudRow>(endpoint, {
      method: "POST",
      body: payload,
    });
    // Показываем регистратору только что созданную запись (ID/статус/история).
    detail.value = response.data;
    internalMode.value = "view";
    editing.value = false;
    emit("saved", detail.value);
    void loadAuditHistory(detail.value);
    void loadRelatedRows(true);
  } finally {
    saving.value = false;
  }
}

async function saveInline() {
  if (isCreate.value) {
    await saveCreate();
    return;
  }

  const row = currentItem.value;
  if (!row) return;
  if (!validateRequiredFields()) return;

  saving.value = true;
  try {
    const payload = buildPayload(props.config.fields);
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

// Сохранение одной строки теста «по-умному»: пустой тест (queued) при первом
// заполнении переводим queued → in_progress → completed двумя командами
// (прямой queued → completed запрещён status_policy), заполненный — командой
// complete, иначе — обычным PATCH черновика. verdict === false — валидное
// заполненное значение, поэтому проверяем строго через `!== null`.
async function saveOneTestRow(row: RelatedRow) {
  const actorId = auth.user?.id;
  const value = (row.value ?? null) as string | null;
  const norm = (row.norm ?? null) as string | null;
  const comment = (row.comment ?? null) as string | null;
  const verdict = (row.verdict ?? null) as boolean | null;
  const isFilled =
    value != null && value !== "" && norm != null && norm !== "" && verdict !== null;
  const touched =
    value != null || norm != null || comment != null || verdict !== null;
  let statusCode = row.statusCode;

  if (statusCode === "queued" && (touched || isFilled)) {
    await apiCommandRequest(`/tests/${row.id}/start`, {
      method: "POST",
      body: { actor_id: actorId },
    });
    statusCode = "in_progress";
  }
  if (isFilled && statusCode === "in_progress") {
    await apiCommandRequest(`/tests/${row.id}/complete`, {
      method: "POST",
      body: { actor_id: actorId, value, norm, comment, verdict },
    });
    return;
  }
  await apiUpdateRequest(`/tests/${row.id}`, {
    method: "PATCH",
    body: { value, norm, comment, verdict },
  });
}

async function saveRelatedTests() {
  if (props.businessKind !== "research") return;

  testsSaving.value = true;
  try {
    await Promise.all(relatedRows.value.map((row) => saveOneTestRow(row)));
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
  <EntityDetailModalShell v-model:active-tab="activeTab" :open="open" :eyebrow="eyebrowText" :title="headerTitle"
    :tabs="tabs" size="xl" :default-fullscreen="true" :ready="Boolean(currentItem)" :breadcrumbs="breadcrumbs"
    :list-items="listItems" :list-label="listLabel" :selected-id="selectedId" :list-has-more="listHasMore"
    :list-loading-more="listLoadingMore" :body-class="activeTab === 'related' ? 'overflow-hidden' : 'overflow-auto'"
    @update:open="emit('update:open', $event)" @select="emit('select', $event)" @list-load-more="emit('list-load-more')"
    @go-to-level="emit('go-to-level', $event)">
    <template #header-actions>
      <SubscribeButton v-if="subscriptionEntity && !isCreate && currentItem?.id" :entity="subscriptionEntity"
        :entity-id="String(currentItem?.id)" />
      <UButton v-if="!editing && businessKind === 'protocols'" label="Предпросмотр" icon="i-lucide-file-search"
        color="neutral" variant="outline" size="sm" @click="openPreview" />
      <UButton v-if="!editing && businessKind === 'protocols'" label="Скачать документ" icon="i-lucide-file-down"
        color="neutral" variant="outline" size="sm" data-testid="protocol-download-document"
        :loading="downloadingKind === 'document'" @click="downloadProtocolFile('document')" />
      <UButton v-if="!editing && businessKind === 'protocols'" label="Сформировать выписку"
        icon="i-lucide-file-warning" color="neutral" variant="outline" size="sm"
        data-testid="protocol-download-excerpt" :loading="downloadingKind === 'excerpt'"
        @click="downloadProtocolFile('excerpt')" />
    </template>

    <template #header>
      <div class="mt-3 flex min-w-0 items-center gap-3">
        <div
          class="flex size-11 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
          <UIcon
            :name="businessKind === 'directions' ? 'i-lucide-clipboard-list' : businessKind === 'samples' ? 'i-lucide-test-tube-2' : businessKind === 'research' ? 'i-lucide-flask-conical' : 'i-lucide-database'"
            class="size-5" />
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="truncate text-2xl font-semibold text-highlighted">
              {{ headerTitle }}
            </h2>
            <UBadge v-if="!isCreate && statusLabel" :color="statusColor" variant="subtle" :label="statusLabel" />
            <UBadge v-if="!isCreate && currentItem?.is_urgent" color="error" variant="subtle" label="Срочно" />
            <UBadge v-if="loadError" color="warning" variant="subtle" label="Данные из таблицы" />
          </div>
          <p class="mt-1 truncate text-sm text-muted">
            {{ subtitle }}
          </p>
        </div>
        <div v-if="!editing && headerActions.length" class="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <UButton v-for="(action, index) in headerActions" :key="index"
            :label="typeof action.label === 'string' ? action.label : ''" :icon="action.icon"
            :color="action.color ?? 'neutral'" variant="subtle" size="sm" :disabled="action.disabled"
            @click="action.onSelect?.($event)" />
        </div>
      </div>
    </template>

    <template #tabs-trailing>
      <UTooltip v-if="!isCreate" text="Технический аудит">
        <UButton icon="i-lucide-list" :color="activeTab === 'technical' ? 'primary' : 'neutral'"
          :variant="activeTab === 'technical' ? 'subtle' : 'ghost'" square size="sm" class="ml-auto"
          data-testid="entity-detail-technical-tab" @click="activeTab = 'technical'" />
      </UTooltip>
    </template>

    <div v-if="loading" class="space-y-3">
      <USkeleton class="h-24 w-full" />
      <USkeleton class="h-64 w-full" />
    </div>

    <div v-else-if="activeTab === 'card'" class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(19rem,25rem)]">
      <section class="min-w-0 space-y-5">
        <!-- Таймлайн образца: от отбора до дедлайна выпуска
        <div v-if="businessKind === 'samples' && statusTimeline.length"
          class="rounded-lg border border-default p-4">
          <p class="mb-4 text-sm font-semibold text-highlighted">
            Таймлайн образца — от отбора до выпуска
          </p>
          <div class="overflow-x-auto pb-1">
            <UTimeline :items="statusTimeline" :model-value="statusCode ?? undefined"
              :color="statusCode === 'rejected' ? 'error' : 'primary'" orientation="horizontal" size="md"
              class="min-w-2xl" :ui="{
                date: 'text-xs font-medium',
                title: 'text-xs font-semibold',
                indicator: 'group-data-[state=active]:ring-2 group-data-[state=active]:ring-primary/30',
              }" />
          </div>
        </div> -->

        <div>
          <EntityFieldGrid :fields="gridFields" :editing="editing" :form-state="formState"
            :reference-options="referenceOptions" :resolve-display="displayFieldValue" @update="setValue" />

          <div class="mt-3 flex items-center justify-end gap-2">
            <UButton v-if="!editing && canEditEntity" label="Редактировать" icon="i-lucide-pencil" color="neutral"
              variant="outline" size="sm" @click="editing = true" />
            <template v-else-if="editing">
              <UButton :label="isCreate ? 'Отмена' : 'Отменить'" color="neutral" variant="outline" size="sm"
                :disabled="saving" @click="cancelEdit" />
              <UButton label="Сохранить" icon="i-lucide-save" color="primary" size="sm" :loading="saving"
                @click="saveInline" />
            </template>
          </div>
        </div>

        <UAlert v-if="loadError" color="warning" variant="subtle" icon="i-lucide-triangle-alert"
          title="Backend вернул ошибку при чтении карточки"
          description="Карточка построена по данным строки таблицы." />
      </section>

      <aside v-if="!isCreate" class="h-full min-w-0">
        <div class="h-full rounded-lg border border-default p-4">
          <div class="mb-3 flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-highlighted">Жизненный цикл</h3>

            <UBadge v-if="!statusTimeline.length" color="neutral" variant="outline"
              :label="`${statusHistory.length} события`" />
          </div>

          <!-- Направления/образцы: строго статусы из таблиц statuses -->
          <UTimeline v-if="statusTimeline.length" :items="statusTimeline" :model-value="statusCode ?? undefined"
            :color="statusCode === 'rejected' ? 'error' : 'primary'" orientation="vertical" size="lg" class="w-full"
            :ui="{
              date: 'text-xs',
              title: 'text-sm font-semibold',
              indicator: 'group-data-[state=active]:ring-2 group-data-[state=active]:ring-primary/30 [&_span]:size-5',
            }" />
          <UStepper v-else-if="statusStepperItems.length" orientation="vertical" :items="statusStepperItems"
            :model-value="activeStatusStepIndex" disabled class="w-full" :ui="timelineStepperUi">
            <template #description="{ item: stepperItem }">
              <div class="space-y-1">
                <p class="whitespace-pre-line break-words text-xs leading-5 text-muted">
                  {{ stepperItem.description }}
                </p>
                <div class="flex flex-wrap items-center gap-2">
                  <UBadge v-if="stepperItem.actor" color="neutral" variant="outline" size="sm"
                    :label="stepperItem.actor" />
                  <p class="font-mono text-xs text-muted">
                    {{ stepperItem.date ? formatDateTime(stepperItem.date) : 'Дата не указана' }}
                  </p>
                </div>
              </div>
            </template>
          </UStepper>
        </div>
      </aside>
    </div>

    <TechnicalAuditTimeline v-else-if="activeTab === 'technical'" :events="technicalAudit" />

    <ResearchWorkflowTab v-else-if="activeTab === 'workflow'" :research="currentItem" />

    <EntityRelatedTab v-else-if="activeTab === 'related'" :business-kind="businessKind" :rows="relatedRows"
      :loading="relatedLoading" :loading-more="relatedLoadingMore" :has-more="relatedHasMore"
      :tests-saving="testsSaving" :can-add-sample="canAddSampleToDirection" @load-more="loadRelatedRows(false)"
      @save-tests="saveRelatedTests" @open-related="emit('open-related', $event)"
      @add-sample="emit('create-related', { kind: 'samples' })" />
  </EntityDetailModalShell>

  <ProtocolPreviewModal v-if="businessKind === 'protocols'" v-model:open="previewOpen" :protocol="currentItem"
    :samples="relatedRows" />
</template>
