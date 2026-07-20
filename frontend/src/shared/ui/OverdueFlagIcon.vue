<script setup lang="ts">
// Индикатор просроченного дедлайна выпуска (зачёркнутый будильник) с единым
// размером и тултипом. Показывать или нет — решает вызывающий код через v-if.
import { useI18n } from "vue-i18n";

const { t } = useI18n();
</script>

<template>
  <UTooltip :text="t('entityDetail.releaseDelayedTitle')">
    <UIcon name="i-lucide-alarm-clock-off" class="size-4 shrink-0 text-error" />
  </UTooltip>
</template>
