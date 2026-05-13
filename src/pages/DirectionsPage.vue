<script setup lang="ts">
import { computed, h, nextTick, ref, resolveComponent, watch, onMounted } from "vue";
import type { DropdownMenuItem, TableColumn } from "@nuxt/ui";
import { useServerTable } from "@/shared/composables/useServerTable";

import CrudTableShell from "@/shared/ui/CrudTableShell.vue";
import CrudSearchControl from "@/shared/ui/CrudSearchControl.vue";
import CrudFilterControls from "@/shared/ui/CrudFilterControls.vue";
import CrudTableEmptyState from "@/shared/ui/CrudTableEmptyState.vue";
import CrudTableLoadingRows from "@/shared/ui/CrudTableLoadingRows.vue";
import RowContextMenu from "@/shared/ui/RowContextMenu.vue";
import {
  borderedCrudTableUi,
  createSkeletonRows,
  isSkeletonRow,
  renderSkeletonCell,
} from "@/shared/ui/table";
import DirectionDetailModal from "@/modules/directions/components/DirectionDetailModal.vue";

interface DirectionSample {
  id: number;
  code: string;
  type: string;
  lab: string;
  status: "pending" | "registered" | "analyzed" | "completed" | "rejected";
  deadline: string;
}

interface Direction {
  id: number;
  number: string;
  object: string;
  doctor: string;
  branch: string;
  status: "draft" | "registered" | "in_progress" | "completed";
  urgency: "normal" | "urgent";
  protocol: "missing" | "draft" | "issued";
  collectedAt: string;
  deadline: string;
  samples: DirectionSample[];
}

const toast = useToast();

// Mock data
const allDirections = ref<Direction[]>([
  {
    id: 1, number: "DIR-2024-001", object: "ООО «Агрокомплекс»", doctor: "Анна Смирнова",
    branch: "Центральный филиал", status: "in_progress", urgency: "normal", protocol: "draft",
    collectedAt: "2024-03-15T10:30:00", deadline: "2024-03-22T10:30:00",
    samples: [
      { id: 1, code: "SMP-001", type: "Смыв", lab: "Микробиология", status: "analyzed", deadline: "2024-03-22T10:30:00" },
      { id: 2, code: "SMP-002", type: "Смыв", lab: "Микробиология", status: "registered", deadline: "2024-03-22T10:30:00" },
      { id: 3, code: "SMP-003", type: "Сыворотка", lab: "Биохимия", status: "pending", deadline: "2024-03-22T10:30:00" },
    ],
  },
  { id: 2, number: "DIR-2024-002", object: "ИП «Иванов»", doctor: "Петр Васильев", branch: "Северный филиал", status: "draft", urgency: "urgent", protocol: "missing", collectedAt: "2024-03-16T14:00:00", deadline: "2024-03-23T14:00:00", samples: [{ id: 4, code: "SMP-004", type: "Кровь", lab: "Гематология", status: "pending", deadline: "2024-03-23T14:00:00" }] },
  { id: 3, number: "DIR-2024-003", object: "ЗАО «Медсервис»", doctor: "Анна Смирнова", branch: "Центральный филиал", status: "completed", urgency: "normal", protocol: "issued", collectedAt: "2024-03-10T09:00:00", deadline: "2024-03-17T09:00:00", samples: [{ id: 5, code: "SMP-005", type: "Моча", lab: "Биохимия", status: "completed", deadline: "2024-03-17T09:00:00" }, { id: 6, code: "SMP-006", type: "Кровь", lab: "Гематология", status: "completed", deadline: "2024-03-17T09:00:00" }] },
]);

type DirectionFilter = "all" | "draft" | "registered" | "in_progress" | "completed";

const query = ref("");
const selectedFilter = ref<DirectionFilter>("all");
const selectedDirection = ref<Direction | null>(null);
const detailOpen = ref(false);
const importOpen = ref(false);
const createOpen = ref(false);
const protocolOpen = ref(false);
const columnVisibility = ref<Record<string, boolean>>({});
const contextRow = ref<Direction | null>(null);
const contextMenuOpen = ref(false);
const contextMenuPosition = ref({ x: 0, y: 0 });
const skeletonRows = createSkeletonRows<Direction>(17);

const filterItems = computed(() => [
  { label: "Все", value: "all" },
  { label: "Draft", value: "draft" },
  { label: "Registered", value: "registered" },
  { label: "В работе", value: "in_progress" },
  { label: "Завершено", value: "completed" },
]);

// Filter and search
const filteredDirections = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase();
  return allDirections.value.filter((direction) => {
    const matchesFilter = selectedFilter.value === "all" || direction.status === selectedFilter.value;
    const matchesQuery = !normalizedQuery
      || direction.number.toLocaleLowerCase().includes(normalizedQuery)
      || direction.object.toLocaleLowerCase().includes(normalizedQuery)
      || direction.doctor.toLocaleLowerCase().includes(normalizedQuery)
      || direction.branch.toLocaleLowerCase().includes(normalizedQuery);
    return matchesFilter && matchesQuery;
  });
});

const table = useServerTable<Direction>(
  async (params) => {
    const offset = Number(params.cursor ?? params.offset ?? 0);
    const limit = Number(params.limit ?? 30);
    const sorted = [...filteredDirections.value].sort((a, b) => {
      const field = String(params.sort_by || "");
      if (!field) return 0;
      const order = params.sort_order === "desc" ? -1 : 1;
      const left = a[field as keyof Direction];
      const right = b[field as keyof Direction];
      return String(left ?? "").localeCompare(String(right ?? ""), "ru") * order;
    });
    const items = sorted.slice(offset, offset + limit);
    const nextOffset = offset + limit;
    const hasMore = nextOffset < sorted.length;
    return {
      items,
      meta: {
        timestamp: new Date().toISOString(),
        requestId: "directions-local",
        version: "mock",
        includesRequested: [],
        includesApplied: [],
        includesAllowed: [],
        total: sorted.length,
        offset,
        limit,
        nextCursor: hasMore ? String(nextOffset) : null,
        hasMore,
      },
    };
  },
  { mode: "infinite", initialPageSize: 30 }
);

const tableRows = computed(() =>
  table.loading.value ? skeletonRows : table.data.value,
);

// Initial fetch in onMounted so skeleton renders first
onMounted(() => { table.fetch() })

// Sync filtered data into the table
watch([query, selectedFilter], () => {
  table.refresh();
});

const statusColors: Record<string, "neutral" | "primary" | "info" | "success"> = {
  draft: "neutral", registered: "primary", in_progress: "info", completed: "success",
};

const directionStatusLabels: Record<string, string> = {
  draft: "Черновик", registered: "Зарегистрировано", in_progress: "В работе", completed: "Завершено",
};

function openDetail(direction: Direction) {
  selectedDirection.value = direction;
  detailOpen.value = true;
}

function createDirection() {
  const nextId = Math.max(...allDirections.value.map((d) => d.id)) + 1;
  const newDirection: Direction = {
    id: nextId, number: `DIR-2024-${String(nextId).padStart(3, "0")}`,
    object: "Новый объект", doctor: "Анна Смирнова", branch: "Центральный филиал",
    status: "draft", urgency: "normal", protocol: "missing",
    collectedAt: new Date().toISOString(), deadline: new Date(Date.now() + 7 * 86400000).toISOString(), samples: [],
  };
  allDirections.value = [newDirection, ...allDirections.value];
  createOpen.value = false;
  selectedDirection.value = newDirection;
  detailOpen.value = true;
  toast.add({ title: "Направление создано", color: "success" });
}

function importDirection() {
  const nextId = Math.max(...allDirections.value.map((d) => d.id)) + 1;
  const newDirection: Direction = {
    id: nextId, number: `DIR-2024-${String(nextId).padStart(3, "0")}`,
    object: "Импортированный объект", doctor: "Анна Смирнова", branch: "Центральный филиал",
    status: "draft", urgency: "normal", protocol: "missing",
    collectedAt: new Date().toISOString(), deadline: new Date(Date.now() + 7 * 86400000).toISOString(), samples: [],
  };
  allDirections.value = [newDirection, ...allDirections.value];
  importOpen.value = false;
  selectedDirection.value = newDirection;
  detailOpen.value = true;
  toast.add({ title: "Импорт создан как draft", color: "success" });
}

function registerSelectedDirection() {
  if (!selectedDirection.value) return;
  selectedDirection.value.status = "registered";
  toast.add({ title: "Направление зарегистрировано", color: "success" });
}

function issueSelectedProtocol() {
  if (!selectedDirection.value) return;
  selectedDirection.value.protocol = "issued";
  protocolOpen.value = false;
  toast.add({ title: "Протокол выпущен", color: "success" });
}

function handleSampleAction(sample: DirectionSample, action: "accept" | "reject") {
  if (action === "accept") {
    sample.status = "registered";
    toast.add({ title: "Образец принят", color: "success" });
  } else {
    sample.status = "rejected";
    toast.add({ title: "Образец отклонён", color: "warning" });
  }
}

const columnMenuItems = computed(() => [
  { field: 'number', header: 'Номер' },
  { field: 'object', header: 'Объект' },
  { field: 'doctor', header: 'Врач' },
  { field: 'branch', header: 'Филиал' },
  { field: 'status', header: 'Статус' },
  { field: 'urgency', header: 'Срочность' },
  { field: 'actions', header: 'Действия' },
].map(col => ({
  label: col.header,
  type: 'checkbox' as const,
  checked: columnVisibility.value[col.field] !== false,
  onUpdateChecked(checked: boolean) {
    columnVisibility.value = {
      ...columnVisibility.value,
      [col.field]: checked,
    }
  },
  onSelect(event?: Event) {
    event?.preventDefault()
  },
})))

// Table columns
const UBadge = resolveComponent("UBadge");
const UButton = resolveComponent("UButton");

function sortableHeader(label: string, field: string) {
  return h(UButton, {
    color: "neutral",
    variant: "ghost",
    label,
    icon:
      table.sorting.value.field !== field
        ? "i-lucide-arrow-up-down"
        : table.sorting.value.order === 1
          ? "i-lucide-arrow-up-narrow-wide"
          : "i-lucide-arrow-down-wide-narrow",
    class: "-mx-2.5",
    onClick: () => table.setSort(field),
  });
}

const directionColumns = computed<TableColumn<Direction>[]>(() => [
  { accessorKey: "number", header: () => sortableHeader("Номер", "number"), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell("number", 0) : h("span", { class: "font-semibold text-highlighted" }, row.original.number) },
  { accessorKey: "object", header: () => sortableHeader("Объект", "object"), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell("object", 1) : row.original.object },
  { accessorKey: "doctor", header: () => sortableHeader("Врач", "doctor"), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell("doctor", 2) : row.original.doctor },
  { accessorKey: "branch", header: () => sortableHeader("Филиал", "branch"), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell("branch", 3) : row.original.branch },
  { accessorKey: "status", header: () => sortableHeader("Статус", "status"), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell("status", 4) : h(UBadge, { color: statusColors[row.original.status], variant: "subtle", label: directionStatusLabels[row.original.status] }) },
  { accessorKey: "urgency", header: () => sortableHeader("Срочность", "urgency"), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell("urgency", 5) : h(UBadge, { color: row.original.urgency === "urgent" ? "warning" : "neutral", variant: "subtle", label: row.original.urgency === "urgent" ? "Срочно" : "Обычно" }) },
  { id: 'actions', header: 'Действия', meta: { class: { td: 'w-auto min-w-[56px] text-right' } } },
]);

const getColumnKey = (column: TableColumn<Direction>) => {
  if ("id" in column && typeof column.id === "string") {
    return column.id;
  }
  if ("accessorKey" in column && typeof column.accessorKey === "string") {
    return column.accessorKey;
  }
  return "";
};

const visibleColumnCount = computed(() =>
  Math.max(
    1,
    directionColumns.value.filter((column) => {
      const key = getColumnKey(column);
      return !key || columnVisibility.value[key] !== false;
    }).length,
  ),
);

const getRowActionItems = (direction: Direction): DropdownMenuItem[] => [
  { label: "Просмотр", icon: "i-lucide-eye", onSelect: () => openDetail(direction) },
];

const handleRowSelect = (_event: Event, row: { original: Direction }) => {
  if (isSkeletonRow(row.original)) {
    return;
  }

  openDetail(row.original);
};

const contextMenuItems = computed(() =>
  contextRow.value ? getRowActionItems(contextRow.value) : [],
);

const handleRowContextmenu = async (event: Event, row: { original: Direction }) => {
  event.preventDefault();
  if (isSkeletonRow(row.original)) {
    return;
  }

  const mouseEvent = event as MouseEvent;
  contextRow.value = row.original;
  contextMenuOpen.value = false;
  contextMenuPosition.value = { x: mouseEvent.clientX, y: mouseEvent.clientY };
  await nextTick();
  contextMenuOpen.value = true;
};
</script>

<template>
  <UDashboardPanel id="directions" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar title="Направления">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton icon="i-lucide-upload" label="Импорт" color="primary" size="sm" @click="importOpen = true" />
          <UButton icon="i-lucide-plus" label="Создать" color="neutral" variant="outline" size="sm" class="ml-2" @click="createOpen = true" />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl
              v-model="query"
              placeholder="Поиск по направлениям"
            />
            <CrudFilterControls
              :active-count="selectedFilter !== 'all' ? 1 : 0"
              @open="selectedFilter = 'all'"
              @clear="selectedFilter = 'all'"
            />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <UButton
              color="neutral"
              variant="subtle"
              icon="i-lucide-refresh-cw"
              label="Обновить"
              @click="table.refresh()"
            />
            <UDropdownMenu
              :items="columnMenuItems"
              :content="{ align: 'end' }"
            >
              <UButton
                label="Столбцы"
                color="neutral"
                variant="subtle"
                trailing-icon="i-lucide-settings-2"
              />
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>

      <UDashboardToolbar>
        <div class="flex w-full items-center gap-1 overflow-x-auto rounded-lg bg-elevated p-1">
          <UButton
            v-for="item in filterItems"
            :key="item.value"
            size="xs"
            :variant="selectedFilter === item.value ? 'solid' : 'ghost'"
            class="shrink-0"
            :label="item.label"
            @click="selectedFilter = item.value as DirectionFilter"
          />
        </div>
      </UDashboardToolbar>
    </template>

    <template #body>
      <CrudTableShell
        mode="infinite"
        :total="table.total.value"
        :loading-more="table.loadingMore.value"
        :has-more="!table.loading.value && table.hasMore.value"
        @load-more="table.loadMore()"
      >
        <template #table>
          <RowContextMenu
            v-model:open="contextMenuOpen"
            :items="contextMenuItems"
            :x="contextMenuPosition.x"
            :y="contextMenuPosition.y"
          />
          <UTable
            v-model:column-visibility="columnVisibility"
            :data="tableRows"
            :columns="directionColumns"
            :loading="false"
            :on-select="handleRowSelect"
            :on-contextmenu="handleRowContextmenu"
            sticky
            :ui="{
              ...borderedCrudTableUi,
              tbody: 'cursor-pointer',
            }"
          >
            <template #body-bottom>
              <tr v-if="!table.loading.value && table.loadingMore.value" class="border-b border-default">
                <td :colspan="visibleColumnCount" class="border-r border-b border-default p-0">
                  <CrudTableLoadingRows compact :columns="visibleColumnCount" />
                </td>
              </tr>
              <tr v-else-if="!table.loading.value && !table.hasMore.value && table.total.value > 0" class="bg-default">
                <td :colspan="visibleColumnCount" class="border-r border-b border-default px-6 py-3 text-center text-xs text-dimmed">
                  Всего записей: {{ table.total.value }}
                </td>
              </tr>
            </template>
            <template #actions-cell="{ row }">
              <USkeleton v-if="isSkeletonRow(row.original)" class="ml-auto h-4 w-8" />
              <UDropdownMenu
                v-else
                :content="{ align: 'end' }"
                :items="getRowActionItems(row.original)"
              >
                <UButton icon="i-lucide-ellipsis-vertical" color="neutral" variant="ghost" size="sm" />
              </UDropdownMenu>
            </template>
            <template #empty>
              <CrudTableEmptyState
                title="Направления не найдены"
                description="Измените фильтры или создайте новое направление."
              />
            </template>
          </UTable>
        </template>
      </CrudTableShell>
    </template>
  </UDashboardPanel>

  <DirectionDetailModal
    v-model:open="detailOpen"
    :direction="selectedDirection"
    @register="registerSelectedDirection"
    @protocol="protocolOpen = true"
    @sample-action="handleSampleAction"
  />

  <!-- Import Modal -->
  <UModal v-model:open="importOpen" title="Импорт направления" description="Файл будет разобран в preview, затем создан draft.">
    <template #body><UFileUpload label="Загрузить файл направления" description="PDF, XLSX или XML" class="w-full" /></template>
    <template #footer><UButton label="Отмена" color="neutral" variant="ghost" @click="importOpen = false" /><UButton label="Создать draft" icon="i-lucide-upload" @click="importDirection" /></template>
  </UModal>

  <!-- Create Modal -->
  <UModal v-model:open="createOpen" title="Создание направления" description="V1 создаёт mock draft, совместимый с будущим API.">
    <template #body><div class="grid gap-3 sm:grid-cols-2"><UInput model-value="Новый объект" placeholder="Объект" /><UInput model-value="Анна Смирнова" placeholder="Врач" /><UInput model-value="Смыв" placeholder="Тип образца" /><USelect model-value="normal" :items="[{ label: 'Обычная', value: 'normal' }, { label: 'Срочная', value: 'urgent' }]" value-key="value" /></div></template>
    <template #footer><UButton label="Отмена" color="neutral" variant="ghost" @click="createOpen = false" /><UButton label="Создать" icon="i-lucide-plus" @click="createDirection" /></template>
  </UModal>

  <!-- Protocol Modal -->
  <UModal v-model:open="protocolOpen" title="Протокол" description="Закрытые образцы собраны в протокол с заключением.">
    <template #body><UTextarea model-value="Заключение: показатели в пределах допустимых значений." autoresize class="w-full" /></template>
    <template #footer><UButton label="Закрыть" color="neutral" variant="ghost" @click="protocolOpen = false" /><UButton v-if="selectedDirection?.protocol !== 'issued'" label="Выпустить" icon="i-lucide-file-check-2" @click="issueSelectedProtocol" /></template>
  </UModal>
</template>
