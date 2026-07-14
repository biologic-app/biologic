<script setup lang="ts">
import { onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useTours } from "@/shared/composables/useTours";

const props = defineProps<{
  scope: string;
}>();

const { t } = useI18n();
const { hasUnseenTour, startAutostart, startBaseTour, engine } = useTours(props.scope);

onMounted(() => {
  void startAutostart();
});
</script>

<template>
  <UTooltip :text="t('tour.menu.tooltip')" :kbds="['T']" placement="bottom">
    <span :data-tour="`${scope}-tour-menu`" class="relative inline-flex">
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

  <UPopover
    :open="engine.open.value"
    :reference="engine.reference.value"
    :content="{
      side: engine.current.value?.side ?? 'bottom',
      align: engine.current.value?.align ?? 'center',
      sideOffset: 8,
    }"
    :dismissible="false"
    arrow
  >
    <template #content>
      <div data-tour-popover class="w-72 space-y-3 p-4">
        <div class="flex items-start justify-between gap-4">
          <p class="font-semibold text-highlighted">
            {{ engine.current.value?.title }}
          </p>
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="xs"
            square
            data-testid="tour-close"
            @click="engine.finish()"
          />
        </div>
        <p class="text-sm text-muted">
          {{ engine.current.value?.body }}
        </p>
        <div class="flex items-center justify-between pt-1">
          <span class="text-xs tabular-nums text-muted">
            {{ engine.index.value + 1 }} / {{ engine.total.value }}
          </span>
          <div class="flex gap-2">
            <UButton
              color="neutral"
              variant="outline"
              size="sm"
              :disabled="!engine.hasPrev.value"
              @click="engine.prev()"
            >
              {{ t("tour.actions.previous") }}
            </UButton>
            <UButton size="sm" @click="engine.next()">
              {{ engine.hasNext.value ? t("tour.actions.next") : t("tour.actions.done") }}
            </UButton>
          </div>
        </div>
      </div>
    </template>
  </UPopover>
</template>
