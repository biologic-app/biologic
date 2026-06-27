<script setup lang="ts">
import { computed, h, resolveComponent } from "vue";
import type { TableColumn } from "@nuxt/ui";
import {
  formatPlain,
  normalizeFormValue,
  type EntityKind,
  type RelatedRow,
  type RelationKind,
} from "@/shared/ui/entity-detail.helpers";

const props = defineProps<{
  businessKind?: EntityKind | null;
  rows: RelatedRow[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  testsSaving: boolean;
}>();

const emit = defineEmits<{
  (event: "load-more"): void;
  (event: "save-tests"): void;
  (event: "open-related", payload: { kind: EntityKind; item: RelatedRow }): void;
}>();

const UBadge = resolveComponent("UBadge");

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

function routeForRelated(kind: RelationKind) {
  if (kind === "samples") return "/samples";
  if (kind === "research") return "/research";
  if (kind === "directions") return "/directions";
  return "/dictionaries/tests";
}
</script>

<template>
  <section class="flex h-full min-h-0 flex-col gap-3">
    <div class="flex shrink-0 items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-highlighted">
        {{ relatedTitle }}
      </h3>
      <div class="flex items-center gap-2">
        <UBadge color="neutral" variant="outline" :label="`${rows.length} записей`" />
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
          :columns="relatedColumns"
          :loading="loading"
          :ui="{ thead: 'sticky top-0 z-10 bg-elevated', th: 'px-4 py-2 text-left text-sm font-semibold text-highlighted', td: 'px-4 py-2 align-middle text-sm text-muted whitespace-nowrap' }"
        />
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
