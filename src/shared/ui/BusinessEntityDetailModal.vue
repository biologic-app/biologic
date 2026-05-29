<script setup lang="ts">
import type { CrudModuleConfig } from "@/pages/CrudModulePage.vue";
import EntityDetailDialogBase from "@/shared/ui/EntityDetailDialogBase.vue";

type EntityKind = "directions" | "samples" | "research";

type CrudRow = {
  id: string | number;
  [key: string]: unknown;
};

defineProps<{
  open: boolean;
  config: CrudModuleConfig;
  item: CrudRow | null;
  businessKind: EntityKind;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
  (event: "open-related", payload: { kind: EntityKind; item: CrudRow }): void;
}>();
</script>

<template>
  <EntityDetailDialogBase
    :open="open"
    :config="config"
    :item="item"
    :business-kind="businessKind"
    @update:open="emit('update:open', $event)"
    @saved="emit('saved', $event)"
    @open-related="emit('open-related', $event)"
  />
</template>
