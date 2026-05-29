import type { TourDefinition } from '@/shared/tour/types'
import { i18n } from '@/shared/i18n'

const t = (key: string) => i18n.global.t(key).toString()

function getBaseIntro(role: string) {
  return role === 'admin'
    ? t('tour.dashboard.base.adminIntro')
    : t('tour.dashboard.base.intro')
}

export const tourRegistry: TourDefinition[] = [
  {
    id: 'dashboard-base',
    scope: 'dashboard',
    version: '1',
    priority: 200,
    autostart: true,
    completionScope: 'role',
    steps: (context) => [
      {
        routeName: 'dashboard',
        popover: {
          title: t('tour.dashboard.base.title'),
          description: getBaseIntro(context.user.role)
        }
      },
      {
        routeName: 'dashboard',
        element: '[data-tour="dashboard-notifications"]',
        popover: {
          title: t('tour.dashboard.base.notificationsTitle'),
          description: t('tour.dashboard.base.notificationsDescription'),
          side: 'bottom',
          align: 'end'
        }
      },
      {
        routeName: 'dashboard',
        element: '[data-tour="dashboard-range"]',
        popover: {
          title: t('tour.dashboard.base.rangeTitle'),
          description: t('tour.dashboard.base.rangeDescription'),
          side: 'bottom',
          align: 'start'
        }
      },
      {
        routeName: 'dashboard',
        element: '[data-tour="dashboard-period"]',
        popover: {
          title: t('tour.dashboard.base.periodTitle'),
          description: t('tour.dashboard.base.periodDescription'),
          side: 'bottom',
          align: 'start'
        }
      },
      {
        routeName: 'dashboard',
        element: '[data-tour="dashboard-tour-menu"]',
        popover: {
          title: t('tour.dashboard.base.tourMenuTitle'),
          description: t('tour.dashboard.base.tourMenuDescription'),
          side: 'bottom',
          align: 'end'
        }
      }
    ]
  }
]
