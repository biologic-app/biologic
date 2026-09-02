<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useAuth } from "@/modules/auth";

const auth = useAuth();
const { t } = useI18n();
const branchName = computed(() => auth.user?.branch?.name?.trim() || null);
</script>

<template>
  <UBadge
    v-if="branchName"
    color="neutral"
    variant="subtle"
    size="sm"
    class="max-w-56 gap-1.5"
    :title="`${t('userMenu.branch')}: ${branchName}`"
  >
    <UIcon name="i-lucide-building-2" class="size-3.5 shrink-0" />
    <span class="truncate">{{ branchName }}</span>
  </UBadge>
</template>
