import type { TourDefinition } from '@/shared/tour/types'
import { i18n } from '@/shared/i18n'

const t = (key: string) => i18n.global.t(key).toString()

export const tourRegistry: TourDefinition[] = [
  {
    id: 'dashboard-base',
    scope: 'dashboard',
    kind: 'onboarding',
    version: '1',
    priority: 200,
    autostart: true,
    completionScope: 'role',
    title: () => t('tour.dashboard.base.title'),
    menuLabel: () => t('tour.dashboard.base.menuLabel'),
    steps: () => [
      {
        popover: {
          title: t('tour.dashboard.base.title'),
          description: t('tour.dashboard.base.intro')
        }
      },
      {
        element: '[data-tour="dashboard-notifications"]',
        popover: {
          title: t('tour.dashboard.base.notificationsTitle'),
          description: t('tour.dashboard.base.notificationsDescription'),
          side: 'bottom',
          align: 'end'
        }
      },
      {
        element: '[data-tour="dashboard-range"]',
        popover: {
          title: t('tour.dashboard.base.rangeTitle'),
          description: t('tour.dashboard.base.rangeDescription'),
          side: 'bottom',
          align: 'start'
        }
      },
      {
        element: '[data-tour="dashboard-period"]',
        popover: {
          title: t('tour.dashboard.base.periodTitle'),
          description: t('tour.dashboard.base.periodDescription'),
          side: 'bottom',
          align: 'start'
        }
      },
      {
        element: '[data-tour="dashboard-quick-actions"]',
        popover: {
          title: t('tour.dashboard.base.quickActionsTitle'),
          description: t('tour.dashboard.base.quickActionsDescription'),
          side: 'left',
          align: 'start'
        }
      },
      {
        element: '[data-tour="dashboard-tour-menu"]',
        popover: {
          title: t('tour.dashboard.base.tourMenuTitle'),
          description: t('tour.dashboard.base.tourMenuDescription'),
          side: 'bottom',
          align: 'end'
        }
      }
    ]
  },
  {
    id: 'dashboard-whats-new-2026-03',
    scope: 'dashboard',
    kind: 'whats-new',
    version: '2026.03',
    priority: 100,
    autostart: true,
    completionScope: 'user',
    title: () => t('tour.dashboard.whatsNew.title'),
    menuLabel: () => t('tour.dashboard.whatsNew.menuLabel'),
    steps: () => [
      {
        popover: {
          title: t('tour.dashboard.whatsNew.title'),
          description: t('tour.dashboard.whatsNew.intro')
        }
      },
      {
        element: '[data-tour="dashboard-tour-menu"]',
        popover: {
          title: t('tour.dashboard.whatsNew.menuTitle'),
          description: t('tour.dashboard.whatsNew.menuDescription'),
          side: 'bottom',
          align: 'end'
        }
      },
      {
        element: '[data-tour="dashboard-stats"]',
        popover: {
          title: t('tour.dashboard.whatsNew.statsTitle'),
          description: t('tour.dashboard.whatsNew.statsDescription'),
          side: 'top',
          align: 'center'
        }
      },
      {
        element: '[data-tour="dashboard-chart"]',
        popover: {
          title: t('tour.dashboard.whatsNew.chartTitle'),
          description: t('tour.dashboard.whatsNew.chartDescription'),
          side: 'top',
          align: 'center'
        }
      }
    ]
  }
]
