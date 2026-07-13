import { ref } from "vue";
import { apiReadListRequest } from "@/shared/api/client.api";
import {
  booleanStatus,
  formatDisplay,
  isRecord,
  namedValue,
  pickText,
  relationLabel,
  type DetailRow,
  type EntityKind,
  type RelatedRow,
  type RelationKind,
} from "@/shared/ui/entity-detail.helpers";
import { resolveStatusCode } from "@/shared/domain/status";

export const RELATED_PAGE_SIZE = 20;
// Вложенных исследований на образец обычно немного — берём с запасом одной
// страницей, без отдельной пагинации внутри дерева.
const SAMPLE_CHILDREN_LIMIT = 50;

// Бэкенд не отдаёт sample_type вложенным объектом (populate только status), а
// колонка «Тип образца» дерева требует имя типа. Резолвим id → name из
// справочника /sample_types один раз на сессию вкладки (кешируем только успех).
let sampleTypeNamesCache: Map<string, string> | null = null;

async function getSampleTypeNames(): Promise<Map<string, string>> {
  if (sampleTypeNamesCache) return sampleTypeNamesCache;
  try {
    const response = await apiReadListRequest<DetailRow>("/sample_types", {
      method: "GET",
      params: { limit: 200 },
    });
    const cache = new Map<string, string>();
    for (const item of response.items) {
      cache.set(String(item.id), namedValue(item));
    }
    sampleTypeNamesCache = cache;
    return cache;
  } catch {
    return new Map();
  }
}

export type RelationRequest = {
  endpoint: string;
  include: string;
  filterKey: string;
  kind: RelationKind;
};

// Связь бизнес-сущности с дочерней коллекцией (направление → образцы и т.д.).
export function relationRequest(businessKind: EntityKind | null | undefined): RelationRequest | null {
  if (businessKind === "directions") {
    return { endpoint: "/samples", include: "sample_type,status,direction,protocol", filterKey: "direction_id", kind: "samples" };
  }
  if (businessKind === "samples") {
    return { endpoint: "/research", include: "sample,research_goal,lab,status", filterKey: "sample_id", kind: "research" };
  }
  if (businessKind === "research") {
    return { endpoint: "/tests", include: "research,indicator,status", filterKey: "research_id", kind: "tests" };
  }
  if (businessKind === "protocols") {
    return { endpoint: "/samples", include: "sample_type,status,direction,protocol", filterKey: "protocol_id", kind: "samples" };
  }
  return null;
}

function normalizeRelatedRow(row: DetailRow, kind: RelationKind): RelatedRow {
  const statusText = namedValue(row.status) || booleanStatus(row) || "-";
  const statusCodeRaw = isRecord(row.status)
    ? (row.status as { code?: unknown }).code
    : undefined;
  const statusCode = resolveStatusCode(
    String(statusCodeRaw ?? statusText).trim().toLowerCase(),
  );
  // Реальный цвет статуса из include=status (бэкенд) — источник для бейджа.
  const statusColor = isRecord(row.status)
    ? ((row.status as { color?: unknown }).color as string | null | undefined) ?? null
    : null;
  return {
    ...row,
    relationKind: kind,
    type: relationLabel(kind),
    title: pickText(row, ["name", "indicator.name", "research_goal.name", "sample.name", "code"]),
    statusText,
    statusCode,
    statusColor,
    updatedAtText: formatDisplay(row.updated_at ?? row.completed_at ?? row.received_at),
    // lab приходит в include исследований; для образцов поле отсутствует → "".
    labName: namedValue(row.lab),
  };
}

// Догрузка исследований для каждого образца страницы (дерево «образец →
// исследования») + резолв имени типа образца. Запросы по образцам — параллельно.
async function attachSampleChildren(samples: RelatedRow[]): Promise<RelatedRow[]> {
  const typeNames = await getSampleTypeNames();
  const childLists = await Promise.all(
    samples.map((sample) =>
      apiReadListRequest<DetailRow>("/research", {
        method: "GET",
        params: {
          limit: SAMPLE_CHILDREN_LIMIT,
          include: "sample,research_goal,lab,status",
          filters: JSON.stringify({ sample_id: sample.id }),
        },
      })
        .then((response) => response.items.map((item) => normalizeRelatedRow(item, "research")))
        .catch(() => [] as RelatedRow[]),
    ),
  );
  return samples.map((sample, index) => ({
    ...sample,
    sampleTypeName:
      typeof sample.sample_type_id === "string"
        ? typeNames.get(sample.sample_type_id) ?? ""
        : "",
    // is_urgent есть только у образца — наследуем на вложенные исследования,
    // чтобы «Срочно» можно было показать на любом уровне дерева.
    children: childLists[index].map((child) => ({ ...child, is_urgent: sample.is_urgent })),
  }));
}

// Пагинация дочерних записей карточки (курсорная, «Загрузить ещё»).
// currentItem/businessKind передаются геттерами, чтобы реактивность жила в SFC.
export function useRelatedEntities(ctx: {
  currentItem: () => DetailRow | null;
  businessKind: () => EntityKind | null | undefined;
}) {
  const relatedRows = ref<RelatedRow[]>([]);
  const relatedLoading = ref(false);
  const relatedLoadingMore = ref(false);
  const relatedCursor = ref<string | null>(null);
  const relatedHasMore = ref(false);

  function reset() {
    relatedRows.value = [];
    relatedCursor.value = null;
    relatedHasMore.value = false;
  }

  async function loadRelatedRows(isReset = false) {
    const row = ctx.currentItem();
    const relation = relationRequest(ctx.businessKind());
    if (!row || !relation) {
      reset();
      return;
    }

    if (isReset) {
      reset();
      relatedLoading.value = true;
    } else {
      relatedLoadingMore.value = true;
    }

    try {
      const response = await apiReadListRequest<DetailRow>(relation.endpoint, {
        method: "GET",
        params: {
          limit: RELATED_PAGE_SIZE,
          cursor: isReset ? undefined : relatedCursor.value,
          include: relation.include,
          filters: JSON.stringify({ [relation.filterKey]: row.id }),
        },
      });
      let nextRows = response.items.map((item) => normalizeRelatedRow(item, relation.kind));
      // Вкладка образцов — дерево: подвешиваем исследования каждого образца.
      if (relation.kind === "samples") {
        nextRows = await attachSampleChildren(nextRows);
      }
      relatedRows.value = isReset ? nextRows : [...relatedRows.value, ...nextRows];
      relatedCursor.value = response.meta.nextCursor ?? null;
      relatedHasMore.value = Boolean(response.meta.hasMore ?? response.meta.nextCursor);
    } catch {
      if (isReset) reset();
    } finally {
      relatedLoading.value = false;
      relatedLoadingMore.value = false;
    }
  }

  return {
    relatedRows,
    relatedLoading,
    relatedLoadingMore,
    relatedCursor,
    relatedHasMore,
    loadRelatedRows,
  };
}
