<script setup lang="ts">
import { computed } from 'vue'
import { useAuth } from '@/modules/auth'
import { resolveDashboardForRole } from '@/modules/dashboard/role-dashboards'

const auth = useAuth()

// The dashboard is role-specific: each role sees a view tailored to its work
// (registrars get the intake dashboard). resolveDashboardForRole falls back to
// the general operational overview for roles without a dedicated one.
const dashboardComponent = computed(() => resolveDashboardForRole(auth.user?.role))
</script>

<template>
  <component :is="dashboardComponent" />
</template>
