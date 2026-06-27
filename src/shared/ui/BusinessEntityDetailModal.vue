<script setup lang="ts">
import type { CrudModuleConfig, CrudRow } from '@/shared/types/crud';
import EntityDetailDialogBase from "@/shared/ui/EntityDetailDialogBase.vue";
import type { DetailListItem } from "@/shared/ui/EntityDetailMasterList.vue";

type EntityKind = "directions" | "samples" | "research";

defineProps<{
  open: boolean;
  config: CrudModuleConfig;
  item: CrudRow | null;
  businessKind: EntityKind;
  listItems?: DetailListItem[];
  listHasMore?: boolean;
  listLoadingMore?: boolean;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
  (event: "open-related", payload: { kind: EntityKind; item: CrudRow }): void;
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
    :list-items="listItems"
    :selected-id="item?.id ?? null"
    :list-has-more="listHasMore"
    :list-loading-more="listLoadingMore"
    @update:open="emit('update:open', $event)"
    @saved="emit('saved', $event)"
    @open-related="emit('open-related', $event)"
    @select="emit('select', $event)"
    @list-load-more="emit('list-load-more')"
  />
</template>
