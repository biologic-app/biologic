<script setup lang="ts">
defineProps<{
  open: boolean;
  title?: string;
  description?: string;
  loading?: boolean;
  confirmLabel?: string;
  confirmColor?: "primary" | "error" | "neutral";
  confirmIcon?: string;
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
</script>

<template>
  <UModal
    :open="open"
    :dismissible="!loading"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <div class="flex flex-col items-center gap-4 py-4 text-center sm:py-6">
        <div
          class="flex size-11 items-center justify-center rounded-full border border-default bg-elevated"
        >
          <UIcon
            :name="confirmColor === 'error' ? 'i-lucide-triangle-alert' : 'i-lucide-circle-help'"
            :class="confirmColor === 'error' ? 'size-5 text-error' : 'size-5 text-muted'"
          />
        </div>
        <div class="space-y-1.5">
          <p class="text-base font-semibold text-highlighted">
            {{ title || "Подтверждение" }}
          </p>
          <p class="max-w-md text-sm text-muted">
            {{ description || "Вы уверены?" }}
          </p>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-end gap-3">
        <UButton
          color="neutral"
          variant="ghost"
          label="Отмена"
          :disabled="loading"
          @click="onCancel"
        />
        <UButton
          :color="confirmColor || 'primary'"
          :loading="loading"
          :label="confirmLabel || 'Подтвердить'"
          :icon="confirmIcon || 'i-lucide-check'"
          @click="onConfirm"
        />
      </div>
    </template>
  </UModal>
</template>
