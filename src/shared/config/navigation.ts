import type { Resource } from '@/shared/types/permissions'

export interface NavigationItem {
  label: string
  icon: string
  to: string
  resource?: Resource
}

export interface NavigationSection {
  title: string
  items: NavigationItem[]
}

export const navigationSections: NavigationSection[] = [
  {
    title: 'Основное',
    items: [
      { label: 'Главная', icon: 'i-lucide-layout-dashboard', to: '/dashboard', resource: 'dashboard' },
      { label: 'Входящие', icon: 'i-lucide-inbox', to: '/inbox', resource: 'inbox' },
      { label: 'Пациенты', icon: 'i-lucide-users', to: '/customers', resource: 'customers' },
      { label: 'Направления', icon: 'i-lucide-file-text', to: '/directions', resource: 'directions' },
      { label: 'Образцы', icon: 'i-lucide-flask-conical', to: '/samples', resource: 'samples' },
      { label: 'Протоколы', icon: 'i-lucide-files', to: '/protocols', resource: 'protocols' },
      { label: 'Результаты', icon: 'i-lucide-chart-column', to: '/results', resource: 'results' },
      { label: 'Заключения', icon: 'i-lucide-file-check', to: '/conclusions', resource: 'conclusions' },
      { label: 'Тесты', icon: 'i-lucide-test-tube', to: '/tests', resource: 'tests' }
    ]
  },
  {
    title: 'Справочники',
    items: [
      { label: 'Врачи', icon: 'i-lucide-stethoscope', to: '/doctors', resource: 'doctors' },
      { label: 'Филиалы', icon: 'i-lucide-building-2', to: '/branches', resource: 'branches' },
      { label: 'Лаборатории', icon: 'i-lucide-building', to: '/labs', resource: 'labs' },
      { label: 'Объекты', icon: 'i-lucide-land-plot', to: '/objects', resource: 'objects' },
      { label: 'Цели исследований', icon: 'i-lucide-target', to: '/research-goals', resource: 'research-goals' },
      { label: 'Цели образцов', icon: 'i-lucide-link', to: '/sample-targets', resource: 'sample-targets' },
      { label: 'Типы образцов', icon: 'i-lucide-beaker', to: '/sample-types', resource: 'sample-types' },
      { label: 'Показатели', icon: 'i-lucide-activity', to: '/indicators', resource: 'indicators' },
      { label: 'Типы протоколов', icon: 'i-lucide-book-copy', to: '/protocol-types', resource: 'protocol-types' },
      { label: 'Статусы', icon: 'i-lucide-circle-check-big', to: '/statuses', resource: 'statuses' }
    ]
  },
  {
    title: 'Администрирование',
    items: [
      { label: 'Пользователи', icon: 'i-lucide-user-cog', to: '/users', resource: 'users' },
      { label: 'Роли', icon: 'i-lucide-shield-check', to: '/user-types', resource: 'user-types' },
      { label: 'Настройки', icon: 'i-lucide-settings', to: '/settings' }
    ]
  }
]
