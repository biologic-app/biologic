<script setup lang="ts">
// Индикатор отслеживания (подписки) сущности: колокольчик «Отслеживается» при
// tracked=true и перечёркнутый «Не отслеживается» при tracked=false. Единый
// размер и тултип; показывать или нет — решает вызывающий код через v-if.
import { useI18n } from "vue-i18n";

withDefaults(defineProps<{ tracked?: boolean }>(), { tracked: false });
const { t } = useI18n();
</script>

<template>
  <UTooltip :text="tracked ? t('crud.isTracked') : t('crud.isNotTracked')">
    <UIcon
      :name="tracked ? 'i-lucide-bell-ring' : 'i-lucide-bell-off'"
      class="size-4 shrink-0"
      :class="tracked ? 'text-success' : 'text-error'"
    />
  </UTooltip>
</template>
