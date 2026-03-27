<script setup lang="ts">
import { useTemplateRef, h, ref, computed, watch, resolveComponent } from "vue";
import type { DropdownMenuItem, TableColumn } from "@nuxt/ui";
import type { TableMeta, Row } from "@tanstack/vue-table";
import { useFetch } from "@vueuse/core";
import { getPaginationRowModel, type Row as TRow } from "@tanstack/table-core";
import { useI18n } from "vue-i18n";
import CustomersAddModal from "@/modules/customers/components/CustomersAddModal.vue";
import CustomersDeleteModal from "@/modules/customers/components/CustomersDeleteModal.vue";
import CustomersFilterModal from "@/modules/customers/components/CustomersFilterModal.vue";
import type { User } from "@/shared/types";

const UAvatar = resolveComponent("UAvatar");
const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");
const UDropdownMenu = resolveComponent("UDropdownMenu");
const UCheckbox = resolveComponent("UCheckbox");

const toast = useToast();
const table = useTemplateRef("table");
const { t } = useI18n();

const columnVisibility = ref();
const rowSelection = ref({ 1: true });

const { data, isFetching } = useFetch(
  "https://dashboard-template.nuxt.dev/api/customers",
  { initialData: [] },
).json<User[]>();

const items: DropdownMenuItem[] = [
  {
    label: "Team",
    icon: "i-lucide-users",
  },
  {
    label: "Invite users",
    icon: "i-lucide-user-plus",
    children: [
      {
        label: "Invite by email",
        icon: "i-lucide-send-horizontal",
      },
      {
        label: "Invite by link",
        icon: "i-lucide-link",
      },
    ],
  },
  {
    label: "New team",
    icon: "i-lucide-plus",
  },
];

function sortableHeader(label: string, column: any) {
  const isSorted = column.getIsSorted();
  return h(UButton, {
    color: "neutral",
    variant: "ghost",
    label,
    icon: isSorted
      ? isSorted === "asc"
        ? "i-lucide-arrow-up-narrow-wide"
        : "i-lucide-arrow-down-wide-narrow"
      : "i-lucide-arrow-up-down",
    class: "-mx-2.5",
    onClick: () => column.toggleSorting(column.getIsSorted() === "asc"),
  });
}

function getStatusLabel(status: User["status"]) {
  return t(`customers.${status}`);
}

function getColumnLabel(id: string) {
  const labels: Record<string, string> = {
    id: t("customers.fields.id"),
    name: t("customers.fields.name"),
    email: t("customers.fields.email"),
    location: t("customers.fields.location"),
    status: t("customers.fields.status"),
  };

  return labels[id] ?? id;
}

function getRowItems(row: TRow<User>) {
  return [
    { type: "label", label: t("customers.actions") },
    {
      label: t("customers.copyId"),
      icon: "i-lucide-copy",
      onSelect() {
        navigator.clipboard.writeText(row.original.id.toString());
        toast.add({
          title: t("customers.copiedTitle"),
          description: t("customers.copiedDescription"),
        });
      },
    },
    { type: "separator" },
    { label: t("customers.viewCard"), icon: "i-lucide-list" },
    { label: t("customers.analysisHistory"), icon: "i-lucide-flask-conical" },
    { type: "separator" },
    {
      label: t("customers.deletePatient"),
      icon: "i-lucide-trash",
      color: "error",
      onSelect() {
        toast.add({ title: t("customers.deletedTitle"), color: "error" });
      },
    },
  ];
}

const columns = computed<TableColumn<User>[]>(() => [
  {
    id: "select",
    enableSorting: false,
    enableHiding: false,
    header: ({ table: currentTable }) =>
      h(UCheckbox, {
        ui: {
          base: "rounded-sm ring ring-inset ring-inverted/40 overflow-hidden focus-visible:outline-2 focus-visible:outline-offset-2",
        },
        modelValue: currentTable.getIsSomePageRowsSelected()
          ? "indeterminate"
          : currentTable.getIsAllPageRowsSelected(),
        "onUpdate:modelValue": (value: boolean | "indeterminate") =>
          currentTable.toggleAllPageRowsSelected(!!value),
        ariaLabel: t("customers.selectAll"),
      }),
    cell: ({ row }) =>
      h(UCheckbox, {
        ui: {
          base: "rounded-sm ring ring-inset ring-inverted/40 overflow-hidden focus-visible:outline-2 focus-visible:outline-offset-2",
        },

        modelValue: row.getIsSelected(),
        "onUpdate:modelValue": (value: boolean | "indeterminate") =>
          row.toggleSelected(!!value),
        ariaLabel: t("customers.selectRow"),
      }),
  },
  {
    accessorKey: "id",
    header: ({ column }) => sortableHeader(t("customers.fields.id"), column),
  },
  {
    accessorKey: "name",
    header: ({ column }) => sortableHeader(t("customers.fields.name"), column),
    cell: ({ row }) =>
      h("div", { class: "flex items-center gap-2" }, [
        h(UAvatar, { ...row.original.avatar, size: "sm" }),
        h("div", undefined, [
          h(
            "p",
            { class: "font-medium text-highlighted text-sm leading-tight" },
            row.original.name,
          ),
          h("p", { class: "text-xs text-muted" }, `@${row.original.name}`),
        ]),
      ]),
  },
  {
    accessorKey: "email",
    header: ({ column }) => sortableHeader(t("customers.fields.email"), column),
    meta: { class: { td: "text-sm text-muted" } },
  },
  {
    accessorKey: "location",
    header: ({ column }) =>
      sortableHeader(t("customers.fields.location"), column),
    cell: ({ row }) => h("span", { class: "text-sm" }, row.original.location),
  },
  {
    accessorKey: "status",
    header: ({ column }) =>
      sortableHeader(t("customers.fields.status"), column),
    filterFn: "equals",
    cell: ({ row }) => {
      const status = row.original.status;
      const color = {
        subscribed: "success" as const,
        unsubscribed: "error" as const,
        bounced: "warning" as const,
      }[status];
      return h(UBadge, { class: "capitalize", variant: "subtle", color }, () =>
        getStatusLabel(status),
      );
    },
  },
  {
    id: "actions",
    enableHiding: false,
    meta: { class: { td: "text-right" } },
    cell: ({ row }) =>
      h(
        "div",
        { class: "text-right" },
        h(
          UDropdownMenu,
          {
            content: { align: "end" },
            items: getRowItems(row),
          },
          () =>
            h(UButton, {
              icon: "i-lucide-ellipsis-vertical",
              color: "neutral",
              variant: "ghost",
              class: "ml-auto",
            }),
        ),
      ),
  },
]);

const tableMeta: TableMeta<User> = {
  class: {
    tr: (row: Row<User>) => {
      const statusClass =
        {
          subscribed:
            "hover:bg-success/10 bg-gradient-to-r from-success/40 to-transparent to-[30%]",
          unsubscribed:
            "hover:bg-error/10 bg-gradient-to-r from-error/40 to-transparent to-[30%]",
          bounced:
            "hover:bg-warning/10 bg-gradient-to-r from-warning/40 to-transparent to-[30%]",
        }[row.original.status] ?? "";

      return row.getIsSelected() ? "" : statusClass;
    },
  },
};

const statusFilter = ref("all");
const statusOptions = computed(() => [
  { label: t("customers.allStatuses"), value: "all" },
  { label: t("customers.subscribed"), value: "subscribed" },
  { label: t("customers.unsubscribed"), value: "unsubscribed" },
  { label: t("customers.bounced"), value: "bounced" },
]);

watch(
  () => statusFilter.value,
  (newValue) => {
    const column = table.value?.tableApi?.getColumn("status");
    if (!column) {
      return;
    }
    column.setFilterValue(newValue === "all" ? undefined : newValue);
  },
);

const pagination = ref({ pageIndex: 0, pageSize: 500 });
</script>

<template>
  <UDashboardPanel
    id="customers"
    resizable
    :ui="{
      body: 'sm:p-0 sm:gap-0',
    }"
  >
    <template #header>
      <UDashboardNavbar :title="t('customers.title')">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UFieldGroup>
            <CustomersAddModal>
              <UButton
                :label="t('customers.create.button')"
                data-tour="customers-create"
                color="primary"
                icon="i-lucide-plus"
              />
            </CustomersAddModal>

            <UDropdownMenu
              :items="items"
              :content="{
                align: 'end',
                side: 'bottom',
                sideOffset: 5,
              }"
            >
              <UButton
                color="primary"
                variant="subtle"
                icon="i-lucide-chevron-down"
              />
            </UDropdownMenu>
          </UFieldGroup>
        </template>
      </UDashboardNavbar>
      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <UFieldGroup>
              <UBadge
                color="neutral"
                variant="outline"
                size="lg"
                icon="i-lucide-search"
                class="px-2"
              />

              <UInput
                v-model="statusFilter"
                :label="t('customers.statusFilter')"
                :options="statusOptions"
                placeholder="Filter by status"
                clearable
                class="pe-1"
              >
                <template v-if="statusFilter?.length" #trailing>
                  <UButton
                    color="neutral"
                    variant="link"
                    size="sm"
                    icon="i-lucide-x"
                    @click="statusFilter = ''"
                  />
                </template>
              </UInput>
            </UFieldGroup>
            <UFieldGroup>
              <CustomersFilterModal>
                <UButton
                  :label="t('common.filter')"
                  color="neutral"
                  variant="subtle"
                  icon="i-lucide-filter"
                >
                  <template #trailing>
                    <UKbd>{{ 5 }}</UKbd>
                  </template>
                </UButton>
              </CustomersFilterModal>
              <UTooltip :text="t('common.clearFilters')"
                ><UButton
                  color="neutral"
                  variant="subtle"
                  size="sm"
                  class="px-2"
                  icon="i-lucide-filter-x"
              /></UTooltip>
            </UFieldGroup>
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <CustomersDeleteModal
              :count="
                table?.tableApi?.getFilteredSelectedRowModel().rows.length
              "
            >
              <UButton
                v-if="
                  table?.tableApi?.getFilteredSelectedRowModel().rows.length
                "
                :label="t('common.delete')"
                color="error"
                variant="subtle"
                icon="i-lucide-trash"
              >
                <template #trailing>
                  <UKbd>{{
                    table?.tableApi?.getFilteredSelectedRowModel().rows.length
                  }}</UKbd>
                </template>
              </UButton>
            </CustomersDeleteModal>
            <UButton
              color="neutral"
              variant="subtle"
              icon="i-lucide-refresh-cw"
              label="Обновить"
            />

            <UDropdownMenu
              :items="
                table?.tableApi
                  ?.getAllColumns()
                  .filter((column: any) => column.getCanHide())
                  .map((column: any) => ({
                    label: getColumnLabel(column.id),
                    type: 'checkbox' as const,
                    checked: column.getIsVisible(),
                    onUpdateChecked(checked: boolean) {
                      column.toggleVisibility(!!checked);
                    },
                    onSelect(event?: Event) {
                      event?.preventDefault();
                    },
                  }))
              "
              :content="{ align: 'end' }"
            >
              <UButton
                :label="t('customers.columns')"
                color="neutral"
                variant="subtle"
                trailing-icon="i-lucide-settings-2"
              />
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <UTable
        ref="table"
        v-model:column-visibility="columnVisibility"
        v-model:row-selection="rowSelection"
        v-model:pagination="pagination"
        :pagination-options="{ getPaginationRowModel: getPaginationRowModel() }"
        :data="data ?? []"
        :columns="columns"
        :meta="tableMeta"
        :loading="isFetching"
        sticky
        :ui="{
          th: 'px-6 py-1.5 text-sm text-highlighted text-left font-semibold',
          td: 'px-6 py-1.5 text-sm text-muted whitespace-nowrap',
        }"
      />
      <div class="flex justify-end border-t border-default py-4 pr-4">
        <UButton
          color="neutral"
          variant="subtle"
          icon="i-lucide-refresh-cw"
          label="Обновить"
        />
        <UPagination
          :page="(table?.tableApi?.getState().pagination.pageIndex || 0) + 1"
          :items-per-page="table?.tableApi?.getState().pagination.pageSize"
          :total="table?.tableApi?.getFilteredRowModel().rows.length"
          @update:page="(p) => table?.tableApi?.setPageIndex(p - 1)"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
