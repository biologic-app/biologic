<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  STATUS_BASE_COLORS,
  STATUS_COLOR_OPTIONS,
  parseStatusColor,
  statusColorAccentVar,
} from '@/shared/domain/status-color'
import { statusColorName } from '@/shared/i18n/status-label'

// Swatch picker for the frontend status-color vocabulary: a trigger showing the
// current color (swatch + readable i18n name) that opens a popover grid of every
// allowed base × modifier option. Selecting a swatch emits its stored token.
const props = defineProps<{ modelValue?: string | null }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const open = ref(false)

// Canonical token of the current value (bare base for the `base` modifier), so
// selection highlighting matches regardless of how the token was stored.
const selectedValue = computed(() => {
  const { base, modifier } = parseStatusColor(props.modelValue)
  return modifier === 'base' ? base : `${base}-${modifier}`
})

// One row per base color, each holding its light/base/dark swatches.
const groups = STATUS_BASE_COLORS.map((base) => ({
  base,
  options: STATUS_COLOR_OPTIONS.filter((option) => option.base === base),
}))

const triggerSwatch = computed(() => statusColorAccentVar(props.modelValue))
const triggerLabel = computed(() => statusColorName(props.modelValue))

const select = (value: string) => {
  emit('update:modelValue', value)
  open.value = false
}
</script>

<template>
  <UPopover v-model:open="open" :content="{ align: 'start' }">
    <UButton
      color="neutral"
      variant="outline"
      class="justify-start w-full"
    >
      <span
        class="size-4 shrink-0 rounded-sm ring-1 ring-default"
        :style="{ backgroundColor: triggerSwatch }"
      />
      <span class="truncate">{{ triggerLabel }}</span>
    </UButton>

    <template #content>
      <div class="max-h-72 overflow-y-auto p-2">
        <div
          v-for="group in groups"
          :key="group.base"
          class="flex items-center gap-2 py-0.5"
        >
          <span class="w-24 shrink-0 truncate text-xs text-muted">
            {{ statusColorName(group.base) }}
          </span>
          <div class="flex gap-1">
            <button
              v-for="option in group.options"
              :key="option.value"
              type="button"
              class="size-6 rounded-md ring-1 ring-default transition-transform hover:scale-110"
              :class="option.value === selectedValue ? 'ring-2 ring-inverted' : ''"
              :style="{ backgroundColor: option.swatch }"
              :title="statusColorName(option.value)"
              :aria-label="statusColorName(option.value)"
              @click="select(option.value)"
            />
          </div>
        </div>
      </div>
    </template>
  </UPopover>
</template>
