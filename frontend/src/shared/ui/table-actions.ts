import { h, resolveComponent } from "vue";
import { useI18n } from "vue-i18n";
import type { TableColumn } from "@nuxt/ui";
import type { Resource } from "@/shared/types/permissions";
import { usePermission } from "@/shared/composables/usePermission";
import { isSkeletonRow, renderSkeletonCell } from "@/shared/ui/table";

export interface ActionColumnHandlers<T = any> {
  onView: (row: T) => void;
  onEdit: (row: T) => void;
  onDelete: (row: T) => void;
}

export function createActionColumn<T = any>(
  resource: Resource,
  handlers: ActionColumnHandlers<T>,
) {
  const { can } = usePermission();
  const { t } = useI18n();

  const canEdit = can(resource, "edit");
  const canDelete = can(resource, "delete");

  return {
    id: "actions",
    header: t("access.columns.actions"),
    meta: { class: { td: "w-auto min-w-[56px] text-right" } },
    cell: ({ row }: { row: { original: T } }) => {
      const UButton = resolveComponent("UButton");
      const UDropdownMenu = resolveComponent("UDropdownMenu");

      const item = row.original;
      if (isSkeletonRow(item)) {
        return renderSkeletonCell("actions");
      }

      const menuItems = [
        {
          label: t("access.actions.view"),
          icon: "i-lucide-eye",
          onSelect: () => handlers.onView(item),
        },
        {
          label: t("access.actions.edit"),
          icon: canEdit ? "i-lucide-pencil" : "i-lucide-lock",
          disabled: !canEdit,
          onSelect: () => handlers.onEdit(item),
        },
        {
          label: t("common.delete"),
          icon: canDelete ? "i-lucide-trash-2" : "i-lucide-lock",
          color: "error" as const,
          disabled: !canDelete,
          onSelect: () => handlers.onDelete(item),
        },
      ];

      return h(
        UDropdownMenu,
        {
          content: { align: "end" },
          items: menuItems,
        },
        () =>
          h(UButton, {
            icon: "i-lucide-ellipsis-vertical",
            color: "neutral",
            variant: "ghost",
            size: "sm",
          }),
      );
    },
  } as TableColumn<T>;
}
