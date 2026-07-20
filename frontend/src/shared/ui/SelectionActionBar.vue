<script setup lang="ts">
import { useI18n } from "vue-i18n"

withDefaults(
  defineProps<{
    count: number
    canDelete?: boolean
  }>(),
  {
    canDelete: true,
  },
)

const emit = defineEmits<{
  clear: []
  delete: []
}>()

const { t } = useI18n()

// Extra (slot) actions inherit the pill surface and keep their own semantic
// colors, so no forced text color is needed.
const actionClass = ""
</script>

<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="translate-y-3 opacity-0"
    leave-active-class="transition duration-150 ease-in"
    leave-to-class="translate-y-3 opacity-0"
  >
    <div
      v-if="count > 0"
      class="absolute bottom-6 left-1/2 z-50 -translate-x-1/2"
    >
      <div class="flex items-center gap-0.5 rounded-2xl bg-elevated px-2 py-2 text-default shadow-2xl ring-1 ring-accented">
        <UBadge
          :label="t('crud.selectedCount', { count })"
          color="primary"
          variant="subtle"
          size="md"
          class="shrink-0 rounded-xl"
        />

        <div class="mx-2 h-5 w-px shrink-0 bg-accented" />

        <slot :action-class="actionClass" :clear="() => emit('clear')" />

        <UButton
          :label="t('common.delete')"
          icon="i-lucide-trash"
          color="error"
          variant="ghost"
          size="sm"
          :disabled="!canDelete"
          @click="emit('delete')"
        />

        <div class="mx-2 h-5 w-px shrink-0 bg-accented" />

        <UButton
          color="neutral"
          variant="ghost"
          size="sm"
          icon="i-lucide-x"
          :aria-label="t('crud.clearSelection')"
          @click="emit('clear')"
        />
      </div>
    </div>
  </Transition>
</template>
