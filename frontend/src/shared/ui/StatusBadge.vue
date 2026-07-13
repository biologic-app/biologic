<script setup lang="ts">
import { computed } from 'vue'
import { statusColorBadgeStyle } from '@/shared/domain/status-color'

// Custom subtle status chip: renders a backend color token via a theme-adaptive
// tint (see `statusColorBadgeStyle`). Replaces `<UBadge :color=...>` for statuses,
// where Nuxt UI's fixed `:color` set can't express arbitrary palette shades.
const props = defineProps<{ color?: string | null; label?: string | null }>()
const badgeStyle = computed(() => statusColorBadgeStyle(props.color))
</script>

<template>
  <span
    class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium leading-5 whitespace-nowrap"
    :style="badgeStyle"
  >
    <slot>{{ label }}</slot>
  </span>
</template>
