<script setup lang="ts">
import type { CrudModuleConfig, CrudRow } from '@/shared/types/crud';
import EntityDetailDialogBase from "@/shared/ui/EntityDetailDialogBase.vue";
import type { DetailListItem } from "@/shared/ui/EntityDetailMasterList.vue";
import type { EntityKind } from "@/shared/ui/entity-detail.helpers";

defineProps<{
  open: boolean;
  config: CrudModuleConfig;
  item: CrudRow | null;
  businessKind: EntityKind;
  listItems?: DetailListItem[];
  listLabel?: string;
  listHasMore?: boolean;
  listLoadingMore?: boolean;
  mode?: "view" | "create";
  startInEdit?: boolean;
  initialValues?: Record<string, unknown> | null;
  breadcrumbs?: Array<{ label: string }>;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
  (event: "open-related", payload: { kind: EntityKind; item: CrudRow }): void;
  (event: "create-related", payload: { kind: EntityKind }): void;
  (event: "go-to-level", index: number): void;
  (event: "select", id: string | number): void;
  (event: "list-load-more"): void;
}>();
</script>

<template>
  <EntityDetailDialogBase
    :open="open"
    :config="config"
    :item="item"
    :business-kind="businessKind"
    :mode="mode"
    :start-in-edit="startInEdit"
    :initial-values="initialValues"
    :breadcrumbs="breadcrumbs"
    :list-items="listItems"
    :list-label="listLabel"
    :selected-id="item?.id ?? null"
    :list-has-more="listHasMore"
    :list-loading-more="listLoadingMore"
    @update:open="emit('update:open', $event)"
    @saved="emit('saved', $event)"
    @open-related="emit('open-related', $event)"
    @create-related="emit('create-related', $event)"
    @go-to-level="emit('go-to-level', $event)"
    @select="emit('select', $event)"
    @list-load-more="emit('list-load-more')"
  />
</template>
