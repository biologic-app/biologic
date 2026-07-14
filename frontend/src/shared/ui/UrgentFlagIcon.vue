<script setup lang="ts">
// Индикатор срочной записи (огонёк) с единым размером и тултипом. Показывать
// или нет — решает вызывающий код через v-if.
import { useI18n } from "vue-i18n";

const { t } = useI18n();
</script>

<template>
  <UTooltip :text="t('crudFields.urgent')">
    <UIcon name="i-lucide-flame" class="size-4 shrink-0 text-red-500" />
  </UTooltip>
</template>
