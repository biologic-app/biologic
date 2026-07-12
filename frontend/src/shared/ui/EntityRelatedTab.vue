<script setup lang="ts">
import { computed, ref } from "vue";
import type { TableColumn } from "@nuxt/ui";
import {
  isSampleDeadlineOverdue,
  normalizeFormValue,
  type EntityKind,
  type RelatedRow,
} from "@/shared/ui/entity-detail.helpers";
import { relationRequest } from "@/shared/composables/useRelatedEntities";
import { getStatusBadgeColor } from "@/shared/domain/status";

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
  (event: "open-related", payload: { kind: EntityKind; item: RelatedRow }): void;
  (event: "add-sample"): void;
}>();

// Вид дочерней коллекции карточки: tests — редактируемая таблица показателей,
// samples — дерево «образец → исследования», research — плоский список.
const relationKind = computed(() => relationRequest(props.businessKind)?.kind ?? null);

// Состояние раскрытия дерева образцов. Пустой объект (не undefined) нужен, чтобы
// UTable подключил onExpandedChange и row.toggleExpanded() работал.
const expanded = ref<Record<string, boolean>>({});

function getSubRows(row: RelatedRow): RelatedRow[] | undefined {
  return row.children;
}

// Дерево образцов: колонка «Тип / Лаборатория» показывает тип образца у
// родителя и лабораторию у дочернего исследования.
const sampleTreeColumns: TableColumn<RelatedRow>[] = [
  { id: "name", header: "Название" },
  { id: "secondary", header: "Тип / Лаборатория" },
  { id: "status", header: "Статус" },
  { accessorKey: "updatedAtText", header: "Обновлено" },
  { id: "actions", header: "" },
];

// Плоский список исследований образца.
const researchColumns: TableColumn<RelatedRow>[] = [
  { accessorKey: "title", header: "Цель исследования" },
  { id: "lab", header: "Лаборатория" },
  { id: "status", header: "Статус" },
  { accessorKey: "updatedAtText", header: "Обновлено" },
  { id: "actions", header: "" },
];

// Вердикт врача по тесту: соответствует / не соответствует / не указано (null).
const verdictOptions = [
  { label: "Соответствует", value: true },
  { label: "Не соответствует", value: false },
];

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
      <UBadge color="neutral" variant="outline" :label="`${rows.length} записей`" />
      <UButton
        v-if="canAddSample"
        label="Добавить образец"
        icon="i-lucide-plus"
        size="sm"
        color="primary"
        data-testid="add-sample-to-direction"
        @click="emit('add-sample')"
      />
      <UButton
        v-if="businessKind === 'research' && rows.length"
        label="Сохранить тесты"
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
                Вердикт врача
              </th>
              <th class="border-b border-default px-3 py-2">
                Комментарий
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
                <UBadge :color="getStatusBadgeColor(row.statusCode)" variant="subtle" :label="row.statusText" />
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
                  placeholder="Не указано"
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
          Связанные элементы не найдены.
        </div>
      </div>
      <div v-if="hasMore" class="shrink-0 border-t border-default px-3 py-2 text-center">
        <UButton
          label="Загрузить ещё"
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
          v-model:expanded="expanded"
          :data="rows"
          :columns="sampleTreeColumns"
          :loading="loading"
          :get-sub-rows="getSubRows"
          :ui="{ thead: 'sticky top-0 z-10 bg-elevated', th: 'px-4 py-2 text-left text-sm font-semibold text-highlighted', td: 'px-4 py-2 align-middle text-sm text-muted whitespace-nowrap' }"
        >
          <template #name-cell="{ row }">
            <div class="flex items-center gap-2" :style="{ paddingLeft: `${row.depth * 1.25}rem` }">
              <UButton
                v-if="row.getCanExpand()"
                variant="ghost"
                color="neutral"
                size="xs"
                :icon="row.getIsExpanded() ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
                :aria-label="row.getIsExpanded() ? 'Свернуть исследования' : 'Развернуть исследования'"
                @click="row.toggleExpanded()"
              />
              <span v-else class="inline-block w-7 shrink-0" />
              <span :class="row.depth === 0 ? 'font-medium text-highlighted' : 'text-muted'">
                {{ row.original.title }}
              </span>
            </div>
          </template>
          <template #secondary-cell="{ row }">
            <span>{{ (row.depth === 0 ? row.original.sampleTypeName : row.original.labName) || '—' }}</span>
          </template>
          <template #status-cell="{ row }">
            <div class="flex items-center gap-2">
              <UBadge
                :color="getStatusBadgeColor(row.original.statusCode)"
                variant="subtle"
                :label="row.original.statusText"
              />
              <UIcon
                v-if="row.depth === 0 && isSampleDeadlineOverdue(row.original)"
                name="i-lucide-alarm-clock-off"
                class="size-4 shrink-0 text-error"
                title="Выпуск задержан"
              />
            </div>
          </template>
          <template #actions-cell="{ row }">
            <div class="flex justify-end">
              <UButton
                icon="i-lucide-panel-top-open"
                color="neutral"
                variant="ghost"
                size="sm"
                aria-label="Открыть карточку"
                @click="openRelated(row.original)"
              />
            </div>
          </template>
        </UTable>
        <div v-if="!loading && !rows.length" class="px-4 py-8 text-center text-sm text-muted">
          Связанные элементы не найдены.
        </div>
      </div>
      <div v-if="hasMore" class="shrink-0 border-t border-default px-3 py-2 text-center">
        <UButton
          label="Загрузить ещё"
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
            <UBadge
              :color="getStatusBadgeColor(row.original.statusCode)"
              variant="subtle"
              :label="row.original.statusText"
            />
          </template>
          <template #actions-cell="{ row }">
            <div class="flex justify-end">
              <UButton
                icon="i-lucide-panel-top-open"
                color="neutral"
                variant="ghost"
                size="sm"
                aria-label="Открыть карточку"
                @click="openRelated(row.original)"
              />
            </div>
          </template>
        </UTable>
        <div v-if="!loading && !rows.length" class="px-4 py-8 text-center text-sm text-muted">
          Связанные элементы не найдены.
        </div>
      </div>
      <div v-if="hasMore" class="shrink-0 border-t border-default px-3 py-2 text-center">
        <UButton
          label="Загрузить ещё"
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
