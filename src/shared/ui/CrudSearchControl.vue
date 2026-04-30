<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

defineProps<{
  modelValue: string;
  placeholder?: string;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
}>();
</script>

<template>
  <UFieldGroup>
    <UBadge
      color="neutral"
      variant="outline"
      size="lg"
      icon="i-lucide-search"
      class="px-2"
    />

    <UInput
      :model-value="modelValue"
      v-bind="$attrs"
      :placeholder="placeholder"
      class="w-full pe-1 sm:w-72"
      @update:model-value="emit('update:modelValue', String($event || ''))"
    >
      <template v-if="modelValue?.length" #trailing>
        <UButton
          color="neutral"
          variant="link"
          size="sm"
          icon="i-lucide-x"
          @click="emit('update:modelValue', '')"
        />
      </template>
    </UInput>
  </UFieldGroup>
</template>
