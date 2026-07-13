// Конечный автомат (FSM) статусов сущностей для графа переходов.
//
// ИСТОЧНИК ПРАВДЫ — backend `ALLOWED_TRANSITIONS` (эндпоинт GET
// /api/v1/status-transitions). Этот модуль хранит только ПРЕЗЕНТАЦИЮ узлов
// (название, иконка) и подписи рёбер, а сам набор рёбер строится из переданных
// пар переходов (`buildEntityFsm`). `STATIC_TRANSITIONS` — зеркало бэкенда,
// используется как мгновенный фолбэк, пока/если API недоступен.
//
// Вид перехода выводится автоматически:
//   reject  — цель `rejected` (терминальная ветка брака/отклонения);
//   loop    — цель раньше источника по оси жизненного цикла (возврат);
//   forward — движение вперёд.

import type { StatusBaseColor } from '@/shared/domain/status-color'

export type FsmEntityKind = 'directions' | 'samples' | 'research' | 'tests'

export type FsmTransitionKind = 'forward' | 'reject' | 'loop'

export interface FsmNode {
  code: string
  name: string
  icon: string
  // Design-system-neutral color name (backend seed palette). Part of the static
  // diagram spec — the graph resolves it through `statusColorVar` for SVG fills.
  color: StatusBaseColor
}

export interface FsmLink {
  source: string
  target: string
  kind: FsmTransitionKind
  label: string
}

export interface EntityFsm {
  nodes: FsmNode[]
  links: FsmLink[]
}

// Тела SVG-иконок Lucide (viewBox 24×24, stroke=currentColor) по коду статуса —
// для отрисовки в центре узлов графа через svgDefs. Код статуса однозначно
// соответствует иконке во всех сущностях.
export const FSM_ICON_BODIES: Record<string, string> = {
  draft: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M14.364 13.634a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506l4.013-4.009a1 1 0 0 0-3.004-3.004zm.123-5.776A1 1 0 0 1 14 7V2"/><path d="M20 19.645V20a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l2.516 2.516M8 18h1"/></g>',
  registered: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14l2 2l4-4"/></g>',
  in_progress: '<path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2M6.453 15h11.094M8.5 2h7"/>',
  partially_completed: '<path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.1 2.182a10 10 0 0 1 3.8 0m0 19.636a10 10 0 0 1-3.8 0m7.509-18.097a10 10 0 0 1 2.69 2.7M2.182 13.9a10 10 0 0 1 0-3.8m18.097 7.509a10 10 0 0 1-2.7 2.69M21.818 10.1a10 10 0 0 1 0 3.8M3.721 6.391a10 10 0 0 1 2.7-2.69m-.03 16.578a10 10 0 0 1-2.69-2.7"/>',
  completed: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m9 12l2 2l4-4"/></g>',
  pending: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11"/></g>',
  analyzed: '<path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18h8M3 22h18m-7 0a7 7 0 1 0 0-14h-1m-4 6h2m-2-2a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Zm3-6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3"/>',
  rejected: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m15 9l-6 6m0-6l6 6"/></g>',
  ordered: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2m4 7h4m-4 5h4m-8-5h.01M8 16h.01"/></g>',
  queued: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M13 5h8m-8 7h8m-8 7h8M3 17l2 2l4-4"/><rect width="6" height="6" x="3" y="4" rx="1"/></g>',
}

// Презентация узлов (порядок = ось жизненного цикла) по каждому виду сущности.
const FSM_NODES: Record<FsmEntityKind, FsmNode[]> = {
  directions: [
    { code: 'draft', name: 'Черновик', icon: 'i-lucide-file-pen-line', color: 'gray' },
    { code: 'registered', name: 'Зарегистрировано', icon: 'i-lucide-clipboard-check', color: 'indigo' },
    { code: 'in_progress', name: 'В работе', icon: 'i-lucide-flask-conical', color: 'blue' },
    { code: 'partially_completed', name: 'Частично выполнено', icon: 'i-lucide-circle-dashed', color: 'lime' },
    { code: 'completed', name: 'Выполнено', icon: 'i-lucide-circle-check', color: 'green' },
  ],
  samples: [
    { code: 'pending', name: 'На регистрации', icon: 'i-lucide-inbox', color: 'amber' },
    { code: 'registered', name: 'Зарегистрирован', icon: 'i-lucide-clipboard-check', color: 'indigo' },
    { code: 'in_progress', name: 'На исследовании', icon: 'i-lucide-flask-conical', color: 'blue' },
    { code: 'analyzed', name: 'Обработан', icon: 'i-lucide-microscope', color: 'violet' },
    { code: 'completed', name: 'Закрыт', icon: 'i-lucide-circle-check', color: 'green' },
    { code: 'rejected', name: 'Брак', icon: 'i-lucide-circle-x', color: 'red' },
  ],
  research: [
    { code: 'draft', name: 'Черновик', icon: 'i-lucide-file-pen-line', color: 'gray' },
    { code: 'ordered', name: 'Заказано', icon: 'i-lucide-clipboard-list', color: 'amber' },
    { code: 'in_progress', name: 'В работе', icon: 'i-lucide-flask-conical', color: 'blue' },
    { code: 'completed', name: 'Завершено', icon: 'i-lucide-circle-check', color: 'green' },
    { code: 'rejected', name: 'Отклонено', icon: 'i-lucide-circle-x', color: 'red' },
  ],
  tests: [
    { code: 'queued', name: 'В очереди', icon: 'i-lucide-list-todo', color: 'amber' },
    { code: 'in_progress', name: 'В работе', icon: 'i-lucide-flask-conical', color: 'blue' },
    { code: 'completed', name: 'Завершено', icon: 'i-lucide-circle-check', color: 'green' },
    { code: 'rejected', name: 'Отклонено', icon: 'i-lucide-circle-x', color: 'red' },
  ],
}

// Подписи рёбер по `${from}->${to}` (по видам — коды пар повторяются между
// сущностями с разным смыслом). Отсутствующая подпись → ребро без текста.
const FSM_LINK_LABELS: Record<FsmEntityKind, Record<string, string>> = {
  directions: {
    'draft->registered': 'Регистрация',
    'registered->in_progress': 'В работу',
    'in_progress->partially_completed': 'Частично',
    'in_progress->completed': 'Завершение',
    'partially_completed->completed': 'Завершение',
  },
  samples: {
    'pending->registered': 'Регистрация',
    'registered->in_progress': 'В работу',
    'registered->rejected': 'Брак',
    'in_progress->analyzed': 'Обработка',
    'in_progress->rejected': 'Брак',
    'analyzed->in_progress': 'Возврат',
    'analyzed->completed': 'Закрытие',
  },
  research: {
    'draft->ordered': 'Подтверждение',
    'draft->rejected': 'Отклонение',
    'ordered->in_progress': 'В работу',
    'ordered->rejected': 'Отклонение',
    'in_progress->completed': 'Завершение',
    'completed->in_progress': 'Возврат',
  },
  tests: {
    'queued->in_progress': 'В работу',
    'queued->rejected': 'Отклонение',
    'in_progress->completed': 'Результат',
    'in_progress->queued': 'В очередь',
    'in_progress->rejected': 'Отклонение',
  },
}

// Зеркало backend ALLOWED_TRANSITIONS — фолбэк, пока API недоступен. Должно
// совпадать с status_policy.py; при рассинхроне побеждает ответ API.
export const STATIC_TRANSITIONS: Record<FsmEntityKind, Array<[string, string]>> = {
  directions: [
    ['draft', 'registered'],
    ['registered', 'in_progress'],
    ['in_progress', 'partially_completed'],
    ['in_progress', 'completed'],
    ['partially_completed', 'completed'],
  ],
  samples: [
    ['pending', 'registered'],
    ['registered', 'in_progress'],
    ['registered', 'rejected'],
    ['in_progress', 'analyzed'],
    ['in_progress', 'rejected'],
    ['analyzed', 'in_progress'],
    ['analyzed', 'completed'],
  ],
  research: [
    ['draft', 'ordered'],
    ['draft', 'rejected'],
    ['ordered', 'in_progress'],
    ['ordered', 'rejected'],
    ['in_progress', 'completed'],
    ['completed', 'in_progress'],
  ],
  tests: [
    ['queued', 'in_progress'],
    ['queued', 'rejected'],
    ['in_progress', 'completed'],
    ['in_progress', 'queued'],
    ['in_progress', 'rejected'],
  ],
}

// Строит FSM (узлы + рёбра) из пар переходов: узлы берутся из презентационного
// каталога (в порядке оси), рёбра — из пар с выведенным видом и подписью.
// Неизвестные коды из API добавляются как узлы-заглушки, чтобы схема не падала.
export const buildEntityFsm = (
  kind: FsmEntityKind,
  pairs: ReadonlyArray<readonly [string, string]>,
): EntityFsm => {
  const catalog = FSM_NODES[kind]
  const order = new Map(catalog.map((node, index) => [node.code, index]))
  const labels = FSM_LINK_LABELS[kind]
  const referenced = new Set<string>()

  const links: FsmLink[] = pairs.map(([from, to]) => {
    referenced.add(from)
    referenced.add(to)
    const kindOf: FsmTransitionKind =
      to === 'rejected'
        ? 'reject'
        : (order.get(to) ?? 0) < (order.get(from) ?? 0)
          ? 'loop'
          : 'forward'
    return { source: from, target: to, kind: kindOf, label: labels[`${from}->${to}`] ?? '' }
  })

  const nodes: FsmNode[] = catalog.filter((node) => referenced.has(node.code))
  const known = new Set(nodes.map((node) => node.code))
  for (const code of referenced) {
    if (!known.has(code)) nodes.push({ code, name: code, icon: 'i-lucide-circle', color: 'gray' })
  }

  return { nodes, links }
}

// FSM из статического фолбэка (мгновенный рендер / офлайн).
export const entityFsm = (kind: FsmEntityKind): EntityFsm =>
  buildEntityFsm(kind, STATIC_TRANSITIONS[kind])

// Русские названия статусов по коду для данной сущности.
export const fsmStatusNames = (kind: FsmEntityKind): Record<string, string> =>
  Object.fromEntries(FSM_NODES[kind].map((node) => [node.code, node.name]))
