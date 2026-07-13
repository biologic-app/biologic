<script setup lang="ts">
// Индикатор срочной записи (огонёк) с единым размером и тултипом. Показывать
// или нет — решает вызывающий код через v-if.
</script>

<template>
  <UTooltip text="Срочно">
    <UIcon name="i-lucide-flame" class="size-5 shrink-0 text-red-500" />
  </UTooltip>
</template>
