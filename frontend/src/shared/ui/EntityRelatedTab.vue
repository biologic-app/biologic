<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { TableColumn } from "@nuxt/ui";
import {
  isRowUrgent,
  isSampleDeadlineOverdue,
  normalizeFormValue,
  type EntityKind,
  type RelatedRow,
} from "@/shared/ui/entity-detail.helpers";
import { relationRequest } from "@/shared/composables/useRelatedEntities";
import { fetchMySubscriptionIds } from "@/shared/api/subscriptions.api";
import StatusBadge from "@/shared/ui/StatusBadge.vue";
import TrackedFlagIcon from "@/shared/ui/TrackedFlagIcon.vue";
import UrgentFlagIcon from "@/shared/ui/UrgentFlagIcon.vue";
import OverdueFlagIcon from "@/shared/ui/OverdueFlagIcon.vue";

const props = defineProps<{
  businessKind?: EntityKind | null;
  rows: RelatedRow[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  testsSaving: boolean;
  canAddSample?: boolean;
}>();

const emit = defineEmits<{
  (event: "load-more"): void;
  (event: "save-tests"): void;
  (event: "open-related", payload: { kind: EntityKind; item: RelatedRow; parent?: { kind: EntityKind; item: RelatedRow } }): void;
  (event: "add-sample"): void;
}>();

const { t } = useI18n();

// Вид дочерней коллекции карточки: tests — редактируемая таблица показателей,
// samples — дерево «образец → исследования», research — плоский список.
const relationKind = computed(() => relationRequest(props.businessKind)?.kind ?? null);

// Ручные подписки текущего пользователя на образцы — питает бейдж
// «Отслеживается» в дереве образцов (аналог pin-колонки в CrudDataTable).
const subscribedSampleIds = ref<Set<string>>(new Set());

watch(
  relationKind,
  async (kind) => {
    if (kind !== "samples") {
      subscribedSampleIds.value = new Set();
      return;
    }
    try {
      const ids = await fetchMySubscriptionIds("samples");
      subscribedSampleIds.value = new Set(ids);
    } catch {
      subscribedSampleIds.value = new Set();
    }
  },
  { immediate: true },
);

function isSampleTracked(row: RelatedRow): boolean {
  return subscribedSampleIds.value.has(String(row.id));
}

// Состояние раскрытия дерева образцов ведём вручную (id раскрытых образцов),
// а не через v-model:expanded/getSubRows: TanStack row.getIsExpanded() при
// таком подключении заставляет UTable рендерить свой собственный пустой
// «expanded»-ряд (см. Table.vue) поверх наших дочерних строк — двойной ряд.
const expandedSampleIds = ref<Set<string | number>>(new Set());

function toggleSampleExpanded(id: string | number) {
  const next = new Set(expandedSampleIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  expandedSampleIds.value = next;
}

// Плоский список строк дерева «образец → исследования» с учётом раскрытия.
const sampleTreeRows = computed<RelatedRow[]>(() => {
  const result: RelatedRow[] = [];
  for (const sample of props.rows) {
    result.push(sample);
    if (sample.children?.length && expandedSampleIds.value.has(sample.id)) {
      result.push(...sample.children);
    }
  }
  return result;
});

function isTopLevelSample(row: RelatedRow): boolean {
  return props.rows.includes(row);
}

function sampleRowDepth(row: RelatedRow): number {
  return isTopLevelSample(row) ? 0 : 1;
}

function canExpandSample(row: RelatedRow): boolean {
  return isTopLevelSample(row) && Boolean(row.children?.length);
}

function isSampleExpanded(row: RelatedRow): boolean {
  return expandedSampleIds.value.has(row.id);
}

// Дерево образцов: колонка «Тип / Лаборатория» показывает тип образца у
// родителя и лабораторию у дочернего исследования.
const sampleTreeColumns = computed<TableColumn<RelatedRow>[]>(() => [
  { id: "name", header: t("access.columns.name") },
  { id: "secondary", header: t("entityRelated.typeOrLab") },
  { id: "status", header: t("common.status") },
  { accessorKey: "updatedAtText", header: t("crudFields.updated") },
  { id: "actions", header: "" },
]);

// Плоский список исследований образца.
const researchColumns = computed<TableColumn<RelatedRow>[]>(() => [
  { accessorKey: "title", header: t("crudFields.researchGoal") },
  { id: "lab", header: t("access.columns.laboratory") },
  { id: "status", header: t("common.status") },
  { accessorKey: "updatedAtText", header: t("crudFields.updated") },
  { id: "actions", header: "" },
]);

// Вердикт врача по тесту: соответствует / не соответствует / не указано (null).
const verdictOptions = computed(() => [
  { label: t("entityRelated.verdictMatches"), value: true },
  { label: t("entityRelated.verdictDoesNotMatch"), value: false },
]);

function relatedString(row: RelatedRow, key: string) {
  const value = row[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function setRelatedValue(row: RelatedRow, key: string, value: unknown) {
  row[key] = normalizeFormValue(value);
}

function openRelated(row: RelatedRow) {
  if (row.relationKind === "tests") return;
  // Исследование в дереве образцов открывается через пропущенный уровень —
  // передаём образец-родителя, чтобы хлебные крошки показали «Направление →
  // Образец → Исследование», а не перепрыгивали сразу к исследованию.
  const parentSample = relationKind.value === "samples" && !isTopLevelSample(row)
    ? props.rows.find((sample) => sample.children?.includes(row))
    : undefined;
  emit("open-related", {
    kind: row.relationKind,
    item: row,
    parent: parentSample ? { kind: "samples" as const, item: parentSample } : undefined,
  });
}

// Модель вердикта для USelect: null (не указано) сводим к undefined, чтобы
// показать плейсхолдер; union-каст держим вне шаблона (иначе `|` ловится
// правилом vue/no-deprecated-filter).
function verdictModel(row: RelatedRow): boolean | undefined {
  return (row.verdict ?? undefined) as boolean | undefined;
}
</script>

<template>
  <section class="flex h-full min-h-0 flex-col gap-3">
    <div class="flex shrink-0 items-center justify-end gap-3">
      <UButton
        v-if="canAddSample"
        :label="t('directionWizard.addSample')"
        icon="i-lucide-plus"
        size="sm"
        color="primary"
        data-testid="add-sample-to-direction"
        @click="emit('add-sample')"
      />
      <UButton
        v-if="businessKind === 'research' && rows.length"
        :label="t('entityRelated.saveTests')"
        icon="i-lucide-save"
        size="sm"
        color="primary"
        :loading="testsSaving"
        @click="emit('save-tests')"
      />
    </div>

    <div
      v-if="relationKind === 'tests'"
      class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-default"
    >
      <div class="min-h-0 flex-1 overflow-auto">
        <table class="w-full min-w-[1040px] border-collapse text-sm">
          <thead class="sticky top-0 z-10 bg-elevated text-left text-xs font-medium uppercase text-muted">
            <tr>
              <th class="border-b border-default px-3 py-2">
                {{ t('crudFields.indicator') }}
              </th>
              <th class="border-b border-default px-3 py-2">
                {{ t('common.status') }}
              </th>
              <th class="border-b border-default px-3 py-2">
                {{ t('workflowCommands.formFields.value') }}
              </th>
              <th class="border-b border-default px-3 py-2">
                {{ t('workflowCommands.formFields.norm') }}
              </th>
              <th class="border-b border-default px-3 py-2">
                {{ t('entityRelated.doctorVerdict') }}
              </th>
              <th class="border-b border-default px-3 py-2">
                {{ t('workflowCommands.formFields.comment') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.id"
              class="border-b border-default last:border-b-0"
            >
              <td class="px-3 py-2 align-top">
                <p class="font-medium text-highlighted">
                  {{ row.title }}
                </p>
              </td>
              <td class="px-3 py-2 align-top">
                <StatusBadge :color="row.statusColor" :label="row.statusText" />
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
                <USelect
                  :model-value="verdictModel(row)"
                  :items="verdictOptions"
                  :placeholder="t('entityRelated.notSpecified')"
                  class="w-full min-w-44"
                  @update:model-value="setRelatedValue(row, 'verdict', $event)"
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
        <div v-if="!loading && !rows.length" class="px-4 py-8 text-center text-sm text-muted">
          {{ t('entityRelated.noRelatedItems') }}
        </div>
      </div>
      <div v-if="hasMore" class="shrink-0 border-t border-default px-3 py-2 text-center">
        <UButton
          :label="t('entityRelated.loadMore')"
          color="neutral"
          variant="outline"
          size="sm"
          :loading="loadingMore"
          @click="emit('load-more')"
        />
      </div>
    </div>

    <div
      v-else-if="relationKind === 'samples'"
      class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-default"
    >
      <div class="min-h-0 flex-1 overflow-auto">
        <UTable
          :data="sampleTreeRows"
          :columns="sampleTreeColumns"
          :loading="loading"
          :ui="{ thead: 'sticky top-0 z-10 bg-elevated', th: 'px-4 py-2 text-left text-sm font-semibold text-highlighted', td: 'px-4 py-2 align-middle text-sm text-muted whitespace-nowrap' }"
        >
          <template #name-cell="{ row }">
            <div class="flex items-center gap-2" :style="{ paddingLeft: `${sampleRowDepth(row.original) * 1.25}rem` }">
              <UButton
                v-if="canExpandSample(row.original)"
                variant="ghost"
                color="neutral"
                size="xs"
                :icon="isSampleExpanded(row.original) ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
                :aria-label="isSampleExpanded(row.original) ? t('entityRelated.collapseResearch') : t('entityRelated.expandResearch')"
                @click="toggleSampleExpanded(row.original.id)"
              />
              <span v-else class="inline-block w-7 shrink-0" />
              <span :class="sampleRowDepth(row.original) === 0 ? 'font-medium text-highlighted' : 'text-muted'">
                {{ row.original.title }}
              </span>
            </div>
          </template>
          <template #secondary-cell="{ row }">
            <span>{{ (sampleRowDepth(row.original) === 0 ? row.original.sampleTypeName : row.original.labName) || '—' }}</span>
          </template>
          <template #status-cell="{ row }">
            <div class="flex items-center gap-2">
              <StatusBadge
                :color="row.original.statusColor"
                :label="row.original.statusText"
              />
              <TrackedFlagIcon
                v-if="sampleRowDepth(row.original) === 0"
                :tracked="isSampleTracked(row.original)"
              />
              <UrgentFlagIcon v-if="isRowUrgent(row.original)" />
              <OverdueFlagIcon
                v-if="sampleRowDepth(row.original) === 0 && isSampleDeadlineOverdue(row.original)"
              />
            </div>
          </template>
          <template #actions-cell="{ row }">
            <div class="flex justify-end">
              <UButton
                icon="i-lucide-external-link"
                color="neutral"
                variant="ghost"
                size="sm"
                :aria-label="t('entityRelated.openCard')"
                @click="openRelated(row.original)"
              />
            </div>
          </template>
        </UTable>
        <div v-if="!loading && !rows.length" class="px-4 py-8 text-center text-sm text-muted">
          {{ t('entityRelated.noRelatedItems') }}
        </div>
      </div>
      <div v-if="hasMore" class="shrink-0 border-t border-default px-3 py-2 text-center">
        <UButton
          :label="t('entityRelated.loadMore')"
          color="neutral"
          variant="outline"
          size="sm"
          :loading="loadingMore"
          @click="emit('load-more')"
        />
      </div>
    </div>

    <div v-else class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-default">
      <div class="min-h-0 flex-1 overflow-auto">
        <UTable
          :data="rows"
          :columns="researchColumns"
          :loading="loading"
          :ui="{ thead: 'sticky top-0 z-10 bg-elevated', th: 'px-4 py-2 text-left text-sm font-semibold text-highlighted', td: 'px-4 py-2 align-middle text-sm text-muted whitespace-nowrap' }"
        >
          <template #title-cell="{ row }">
            <span class="font-medium text-highlighted">{{ row.original.title }}</span>
          </template>
          <template #lab-cell="{ row }">
            <span>{{ row.original.labName || '—' }}</span>
          </template>
          <template #status-cell="{ row }">
            <div class="flex items-center gap-2">
              <StatusBadge
                :color="row.original.statusColor"
                :label="row.original.statusText"
              />
              <UrgentFlagIcon v-if="isRowUrgent(row.original)" />
            </div>
          </template>
          <template #actions-cell="{ row }">
            <div class="flex justify-end">
              <UButton
                icon="i-lucide-external-link"
                color="neutral"
                variant="ghost"
                size="sm"
                :aria-label="t('entityRelated.openCard')"
                @click="openRelated(row.original)"
              />
            </div>
          </template>
        </UTable>
        <div v-if="!loading && !rows.length" class="px-4 py-8 text-center text-sm text-muted">
          {{ t('entityRelated.noRelatedItems') }}
        </div>
      </div>
      <div v-if="hasMore" class="shrink-0 border-t border-default px-3 py-2 text-center">
        <UButton
          :label="t('entityRelated.loadMore')"
          color="neutral"
          variant="outline"
          size="sm"
          :loading="loadingMore"
          @click="emit('load-more')"
        />
      </div>
    </div>
  </section>
</template>
