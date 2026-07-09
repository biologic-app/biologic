<script setup lang="ts">
import type { DropdownMenuItem } from "@nuxt/ui";

defineProps<{
  items: DropdownMenuItem[];
  x: number;
  y: number;
}>();

const open = defineModel<boolean>("open", { default: false });
</script>

<template>
  <UDropdownMenu
    v-model:open="open"
    :items="items"
    :content="{ align: 'start', side: 'bottom', sideOffset: 2 }"
  >
    <button
      type="button"
      tabindex="-1"
      aria-hidden="true"
      class="fixed z-50 size-px opacity-0"
      :style="{ left: `${x}px`, top: `${y}px` }"
    />
  </UDropdownMenu>
</template>
