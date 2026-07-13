<script setup lang="ts">
// Индикатор просроченного дедлайна выпуска (зачёркнутый будильник) с единым
// размером и тултипом. Показывать или нет — решает вызывающий код через v-if.
</script>

<template>
  <UTooltip text="Выпуск задержан">
    <UIcon name="i-lucide-alarm-clock-off" class="size-5 shrink-0 text-error" />
  </UTooltip>
</template>
