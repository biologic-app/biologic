<script setup lang="ts">
import { computed, onMounted } from "vue";
import type { DropdownMenuItem } from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import { useTours } from "@/shared/composables/useTours";

const props = defineProps<{
  scope: string;
}>();

const { t } = useI18n();
const {
  onboardingTour,
  whatsNewTours,
  hasUnseenTours,
  startAutostart,
  startLatestWhatsNew,
  startOnboarding,
  startTour,
} = useTours(props.scope);

const items = computed<DropdownMenuItem[][]>(() => {
  const primaryItems: DropdownMenuItem[] = [];
  const whatsNewItems: DropdownMenuItem[] = [];
  const labelGroup: DropdownMenuItem[] = [
    {
      type: "label",
      label: t("tour.menu.title"),
    },
  ];

  if (onboardingTour.value) {
    primaryItems.push({
      label: t("tour.menu.startBase"),
      icon: "i-lucide-play-circle",
      onSelect: () => startOnboarding(),
    });
  }

  whatsNewTours.value.forEach((tour) => {
    whatsNewItems.push({
      label: tour.menuLabelText,
      icon: tour.seen ? "i-lucide-sparkles" : "i-lucide-badge-plus",
      onSelect: () => startTour(tour.id),
    });
  });

  if (whatsNewTours.value.length) {
    primaryItems.push({
      label: hasUnseenTours.value
        ? t("tour.menu.openWhatsNew")
        : t("tour.menu.replayWhatsNew"),
      icon: "i-lucide-sparkles",
      onSelect: () => startLatestWhatsNew(),
    });
  }

  return [
    labelGroup,
    primaryItems,
    whatsNewItems.length
      ? whatsNewItems
      : [
          {
            label: t("tour.menu.noWhatsNew"),
            icon: "i-lucide-check",
            disabled: true,
          },
        ],
  ].filter((group) => group.length);
});

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
          v-if="hasUnseenTours"
          class="absolute right-2 top-2 size-2 rounded-full bg-[var(--ui-primary)] ring-2 ring-default"
        />
      </span>
    </UTooltip>
  </UDropdownMenu>
</template>
