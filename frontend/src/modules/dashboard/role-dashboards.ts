import OverviewDashboard from '@/modules/dashboard/components/OverviewDashboard.vue'
import RegistrarDashboard from '@/modules/dashboard/components/RegistrarDashboard.vue'
import type { Component } from 'vue'

/**
 * Per-role dashboard registry. Each role can render a tailored dashboard;
 * roles without a dedicated one fall back to the general operational overview.
 * Add an entry here (keyed by the backend `role_key`) to give another role its
 * own dashboard.
 */
const ROLE_DASHBOARDS: Record<string, Component> = {
  registrar: RegistrarDashboard
}


export const resolveDashboardForRole = (role: string | null | undefined): Component =>
  (role ? ROLE_DASHBOARDS[role] : undefined) ?? OverviewDashboard
