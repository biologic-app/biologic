<script setup lang="ts">
export interface SelectionAction {
  label: string
  icon?: string
  color?: "primary" | "success" | "warning" | "error" | "neutral"
  disabled?: boolean
  onClick: () => void
}

defineProps<{
  count: number
  actions: SelectionAction[]
}>()

const emit = defineEmits<{
  clear: []
}>()
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
      class="fixed bottom-6 left-1/2 z-50 -translate-x-1/2"
    >
      <div class="flex items-center gap-0.5 rounded-full bg-inverted px-2 py-1.5 shadow-2xl ring-1 ring-inset ring-white/10">
        <div class="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 text-sm font-semibold text-white">
          <span>{{ count }}</span>
          <span class="text-white/75 font-normal">выбрано</span>
        </div>

        <div class="mx-1.5 h-5 w-px bg-white/15 shrink-0" />

        <template v-for="(action, i) in actions" :key="i">
          <button
            :disabled="action.disabled"
            class="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40"
            :class="{
              'text-white/90 hover:bg-white/10 hover:text-white': !action.color || action.color === 'neutral',
              'text-primary-300 hover:bg-white/10': action.color === 'primary',
              'text-success-300 hover:bg-white/10': action.color === 'success',
              'text-warning-300 hover:bg-white/10': action.color === 'warning',
              'text-error-400 hover:bg-error/10': action.color === 'error',
            }"
            @click="!action.disabled && action.onClick()"
          >
            <UIcon v-if="action.icon" :name="action.icon" class="size-4 shrink-0" />
            {{ action.label }}
          </button>
        </template>

        <div class="mx-1.5 h-5 w-px bg-white/15 shrink-0" />

        <button
          class="flex size-7 items-center justify-center rounded-full text-white/50 transition-colors hover:bg-white/10 hover:text-white"
          @click="emit('clear')"
        >
          <UIcon name="i-lucide-x" class="size-4" />
        </button>
      </div>
    </div>
  </Transition>
</template>
