import { ref } from "vue";
import { apiReadListRequest } from "@/shared/api/client.api";
import {
  booleanStatus,
  formatDisplay,
  namedValue,
  pickText,
  relationLabel,
  type DetailRow,
  type EntityKind,
  type RelatedRow,
  type RelationKind,
} from "@/shared/ui/entity-detail.helpers";

const RELATED_PAGE_SIZE = 20;

type RelationRequest = {
  endpoint: string;
  include: string;
  filterKey: string;
  kind: RelationKind;
};

// Связь бизнес-сущности с дочерней коллекцией (направление → образцы и т.д.).
function relationRequest(businessKind: EntityKind | null | undefined): RelationRequest | null {
  if (businessKind === "directions") {
    return { endpoint: "/samples", include: "sample_type,status,direction,protocol", filterKey: "direction_id", kind: "samples" };
  }
  if (businessKind === "samples") {
    return { endpoint: "/research", include: "sample,research_goal,lab,status", filterKey: "sample_id", kind: "research" };
  }
  if (businessKind === "research") {
    return { endpoint: "/tests", include: "research,indicator,status", filterKey: "research_id", kind: "tests" };
  }
  return null;
}

function normalizeRelatedRow(row: DetailRow, kind: RelationKind): RelatedRow {
  return {
    ...row,
    relationKind: kind,
    type: relationLabel(kind),
    title: pickText(row, ["name", "indicator.name", "research_goal.name", "sample.name", "code"]),
    statusText: namedValue(row.status) || booleanStatus(row) || "-",
    updatedAtText: formatDisplay(row.updated_at ?? row.completed_at ?? row.received_at),
  };
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
      const nextRows = response.items.map((item) => normalizeRelatedRow(item, relation.kind));
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
