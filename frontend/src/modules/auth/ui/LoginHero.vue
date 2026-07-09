<script setup lang="ts">
defineProps<{
  badgeText: string;
  title: string;
  description: string;
}>();
</script>
<template>
  <div class="max-w-2xl space-y-8">
    <UBadge :label="badgeText" variant="subtle" color="primary" size="xl" />
    <div class="space-y-4">
      <h1
        class="max-w-xl text-5xl font-semibold tracking-tight text-highlighted"
      >
        {{ title }}
      </h1>
      <p class="max-w-xl text-lg leading-8 text-toned">
        {{ description }}
      </p>
    </div>
  </div>
</template>
