<script setup lang="ts">
import { computed, onMounted } from "vue";
import type { DropdownMenuItem } from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import { useTours } from "@/shared/composables/useTours";

const props = defineProps<{
  scope: string;
}>();

const { t } = useI18n();
const { tour, hasUnseenTour, startAutostart, startBaseTour, startWhatsNew } =
  useTours(props.scope);

const items = computed<DropdownMenuItem[][]>(() => {
  const labelGroup: DropdownMenuItem[] = [
    {
      type: "label",
      label: t("tour.menu.title"),
    },
  ];
  const actionItems: DropdownMenuItem[] = [
    {
      label: t("tour.menu.startBase"),
      icon: "i-lucide-play-circle",
      onSelect: () => startBaseTour(),
    },
    {
      label: t("tour.menu.openWhatsNew"),
      icon: "i-lucide-sparkles",
      onSelect: () => startWhatsNew(),
    },
  ];

  return tour.value ? [labelGroup, actionItems] : [labelGroup];
})

onMounted(() => {
  void startAutostart();
});
</script>

<template>
  <UDropdownMenu
    :items="items"
    :content="{ align: 'end', collisionPadding: 12 }"
    :ui="{ content: 'w-72' }"
  >
    <UTooltip :text="t('tour.menu.tooltip')" :kbds="['T']" placement="bottom">
      <span data-tour="dashboard-tour-menu" class="relative inline-flex">
        <UButton
          icon="i-lucide-compass"
          color="neutral"
          variant="ghost"
          square
        />
        <span
          v-if="hasUnseenTour"
          class="absolute right-2 top-2 size-2 rounded-full bg-[var(--ui-primary)] ring-2 ring-default"
        />
      </span>
    </UTooltip>
  </UDropdownMenu>
</template>
