<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{
  open: boolean;
  title?: string;
  description?: string;
  loading?: boolean;
  confirmLabel?: string;
  confirmColor?: "primary" | "error" | "neutral";
  confirmIcon?: string;
  // Приподнимает окно над другой открытой модалкой (карточкой сущности):
  // у модалок Nuxt UI нет z-index, порядок определяется телепортом в body,
  // поэтому запущенное из карточки подтверждение иначе оказывается под ней.
  elevated?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:open", value: boolean): void;
  (e: "confirm"): void;
  (e: "cancel"): void;
}>();

function onCancel() {
  emit("cancel");
  emit("update:open", false);
}

function onConfirm() {
  emit("confirm");
}

const { t } = useI18n();
</script>

<template>
  <UModal
    :open="open"
    :title="title || t('permissions.actionLabels.confirm')"
    :dismissible="!loading"
    :ui="{
      content: `w-[calc(100vw-2rem)] max-w-[420px]${elevated ? ' z-[60]' : ''}`,
      overlay: elevated ? 'z-[60]' : undefined,
      header: 'min-h-0 px-5 py-4 sm:px-5',
      body: 'px-5 py-4 sm:px-5 sm:py-4',
      footer: 'px-5 py-3 sm:px-5',
      close: 'top-3.5 end-4'
    }"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <div class="flex items-start gap-3">
        <div
          class="flex size-11 shrink-0 items-center justify-center rounded-full border border-default bg-elevated"
        >
          <UIcon
            :name="confirmColor === 'error' ? 'i-lucide-triangle-alert' : 'i-lucide-circle-help'"
            :class="confirmColor === 'error' ? 'size-5 text-error' : 'size-5 text-muted'"
          />
        </div>
        <div class="min-w-0 pt-0.5">
          <p class="text-sm leading-5 text-muted">
            {{ description || t('crud.areYouSure') }}
          </p>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-end gap-2">
        <UButton
          color="neutral"
          variant="ghost"
          :label="t('common.cancel')"
          :disabled="loading"
          @click="onCancel"
        />
        <UButton
          :color="confirmColor || 'primary'"
          :loading="loading"
          :label="confirmLabel || t('workflowCommands.confirmResearch_selection')"
          :icon="confirmIcon || 'i-lucide-check'"
          @click="onConfirm"
        />
      </div>
    </template>
  </UModal>
</template>
