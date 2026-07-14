import type { AppTourStep, TourDefinition } from '@/shared/tour/types'
import { i18n } from '@/shared/i18n'

const t = (key: string) => i18n.global.t(key).toString()

function getBaseIntro(role: string) {
  return role === 'admin'
    ? t('tour.dashboard.base.adminIntro')
    : t('tour.dashboard.base.intro')
}

function dataTourTarget(attr: string): AppTourStep['target'] {
  return () => document.querySelector(`[data-tour="${attr}"]`) ?? undefined
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
        title: t('tour.dashboard.base.title'),
        body: getBaseIntro(context.user.role)
      },
      {
        routeName: 'dashboard',
        target: dataTourTarget('dashboard-notifications'),
        title: t('tour.dashboard.base.notificationsTitle'),
        body: t('tour.dashboard.base.notificationsDescription'),
        side: 'bottom',
        align: 'end'
      },
      {
        routeName: 'dashboard',
        target: dataTourTarget('dashboard-range'),
        title: t('tour.dashboard.base.rangeTitle'),
        body: t('tour.dashboard.base.rangeDescription'),
        side: 'bottom',
        align: 'start'
      },
      {
        routeName: 'dashboard',
        target: dataTourTarget('dashboard-period'),
        title: t('tour.dashboard.base.periodTitle'),
        body: t('tour.dashboard.base.periodDescription'),
        side: 'bottom',
        align: 'start'
      },
      {
        routeName: 'dashboard',
        target: dataTourTarget('dashboard-tour-menu'),
        title: t('tour.dashboard.base.tourMenuTitle'),
        body: t('tour.dashboard.base.tourMenuDescription'),
        side: 'bottom',
        align: 'end'
      }
    ]
  }
]
