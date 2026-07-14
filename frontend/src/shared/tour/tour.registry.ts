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

// Общие шаги по тулбару таблицы (поиск/фильтры/обновление/столбцы/таблица) —
// одинаковы для всех страниц на WorkflowCrudPage, различается только routeName.
function crudToolbarSteps(routeName: string): AppTourStep[] {
  return [
    {
      routeName,
      target: dataTourTarget('crud-search'),
      title: t('tour.crud.searchTitle'),
      body: t('tour.crud.searchDescription'),
      side: 'bottom',
      align: 'start'
    },
    {
      routeName,
      target: dataTourTarget('crud-filter'),
      title: t('tour.crud.filterTitle'),
      body: t('tour.crud.filterDescription'),
      side: 'bottom',
      align: 'start'
    },
    {
      routeName,
      target: dataTourTarget('crud-refresh'),
      title: t('tour.crud.refreshTitle'),
      body: t('tour.crud.refreshDescription'),
      side: 'bottom',
      align: 'end'
    },
    {
      routeName,
      target: dataTourTarget('crud-columns'),
      title: t('tour.crud.columnsTitle'),
      body: t('tour.crud.columnsDescription'),
      side: 'bottom',
      align: 'end'
    },
    {
      routeName,
      target: dataTourTarget('crud-table'),
      title: t('tour.crud.tableTitle'),
      body: t('tour.crud.tableDescription'),
      side: 'top',
      align: 'center'
    }
  ]
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
  },
  {
    id: 'directions-base',
    scope: 'directions',
    version: '1',
    priority: 200,
    autostart: true,
    completionScope: 'role',
    steps: () => [
      {
        routeName: 'directions',
        title: t('tour.directions.base.title'),
        body: t('tour.directions.base.intro')
      },
      ...crudToolbarSteps('directions'),
      {
        routeName: 'directions',
        target: dataTourTarget('directions-create'),
        title: t('tour.directions.base.createButtonTitle'),
        body: t('tour.directions.base.createButtonDescription'),
        side: 'bottom',
        align: 'end'
      },
      {
        routeName: 'directions',
        action: 'directions-create',
        target: dataTourTarget('directions-wizard-intro'),
        title: t('tour.directions.base.modalTitle'),
        body: t('tour.directions.base.modalDescription'),
        side: 'bottom',
        align: 'center'
      }
    ]
  },
  {
    id: 'research-base',
    scope: 'research',
    version: '1',
    priority: 200,
    autostart: true,
    completionScope: 'role',
    steps: () => [
      {
        routeName: 'research',
        title: t('tour.research.base.title'),
        body: t('tour.research.base.intro')
      },
      ...crudToolbarSteps('research'),
      {
        routeName: 'research',
        action: 'research-open-detail',
        target: dataTourTarget('entity-detail-header'),
        title: t('tour.research.base.modalTitle'),
        body: t('tour.research.base.modalDescription'),
        side: 'bottom',
        align: 'center'
      }
    ]
  },
  {
    id: 'samples-base',
    scope: 'samples',
    version: '1',
    priority: 200,
    autostart: true,
    completionScope: 'role',
    steps: () => [
      {
        routeName: 'samples',
        title: t('tour.samples.base.title'),
        body: t('tour.samples.base.intro')
      },
      ...crudToolbarSteps('samples'),
      {
        routeName: 'samples',
        action: 'samples-open-detail',
        target: dataTourTarget('entity-detail-header'),
        title: t('tour.samples.base.modalTitle'),
        body: t('tour.samples.base.modalDescription'),
        side: 'bottom',
        align: 'center'
      }
    ]
  }
]
