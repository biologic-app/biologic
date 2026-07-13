<script setup lang="ts">
// Индикатор отслеживания (подписки) сущности: колокольчик «Отслеживается» при
// tracked=true и перечёркнутый «Не отслеживается» при tracked=false. Единый
// размер и тултип; показывать или нет — решает вызывающий код через v-if.
withDefaults(defineProps<{ tracked?: boolean }>(), { tracked: false });
</script>

<template>
  <UTooltip :text="tracked ? 'Отслеживается' : 'Не отслеживается'">
    <UIcon
      :name="tracked ? 'i-lucide-bell-ring' : 'i-lucide-bell-off'"
      class="size-5 shrink-0"
      :class="tracked ? 'text-success' : 'text-error'"
    />
  </UTooltip>
</template>
