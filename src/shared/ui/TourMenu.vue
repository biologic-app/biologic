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

onMounted(() => {
  void startAutostart();
});
</script>

<template>
  <UTooltip :text="t('tour.tooltip')" :kbds="['T']" placement="bottom">
    <span data-tour="dashboard-tour-menu" class="relative inline-flex">
      <UButton
        icon="i-lucide-compass"
        color="neutral"
        variant="ghost"
        square
        @click="startBaseTour()"
      />
      <span
        v-if="hasUnseenTour"
        class="absolute right-2 top-2 size-2 rounded-full bg-[var(--ui-primary)] ring-2 ring-default"
      />
    </span>
  </UTooltip>
</template>
