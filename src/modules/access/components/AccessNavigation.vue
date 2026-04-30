<script setup lang="ts">
import { computed } from "vue";
import type { NavigationMenuItem } from "@nuxt/ui";
import { accessItems } from "@/modules/access/config";

const items = computed<NavigationMenuItem[][]>(() => [
  accessItems.map((item) => ({
    label: item.label,
    icon: item.icon,
    to: item.to,
    exact: true,
  })),
]);
</script>

<template>
  <UNavigationMenu :items="items" highlight class="-mx-1" />
</template>
