<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { VisSingleContainer, VisGraph } from '@unovis/vue'
import {
  buildEntityFsm,
  entityFsm,
  FSM_ICON_BODIES,
  type FsmEntityKind,
  type FsmLink,
  type FsmNode,
} from '@/shared/domain/status-fsm'
import { useStatusTransitions } from '@/shared/composables/useStatusTransitions'
import { statusLabel, type StatusEntity } from '@/shared/i18n/status-label'

// Граф конечного автомата статусов сущности. Узлы — статусы (иконка в центре,
// подпись снизу), рёбра — разрешённые переходы (backend `ALLOWED_TRANSITIONS`,
// эндпоинт GET /api/v1/status-transitions). Схема НЕ привязана к текущей записи:
// она показывает весь процесс перехода целиком, а поток частиц анимируется по
// ВСЕМ рёбрам к терминальным статусам. Единственный цвет схемы — primary из
// дизайн-системы Nuxt UI. Подпись узла — код статуса, переведённый через i18n.
const props = defineProps<{
  kind: FsmEntityKind
}>()

const { t } = useI18n()

// Разрешённые переходы: приоритет — ответ API (единый источник правды), фолбэк —
// зеркало STATIC_TRANSITIONS, пока/если запрос не завершён или упал.
const { transitions } = useStatusTransitions()
const fsm = computed(() => {
  const pairs = transitions.value?.[props.kind]
  return pairs ? buildEntityFsm(props.kind, pairs) : entityFsm(props.kind)
})

// i18n-неймспейс статуса скоупится по единственному числу сущности.
const ENTITY_BY_KIND: Record<FsmEntityKind, StatusEntity> = {
  directions: 'direction',
  samples: 'sample',
  research: 'research',
  tests: 'test',
}

// Единственный цвет схемы — primary из Nuxt UI (`--ui-primary`). Резолвим в
// конкретный rgb/hex через временный элемент (в SVG-атрибутах var() не работает),
// чтобы цвет оставался темозависимым. Fallback — зелёный на ранний рендер.
const primaryColor = ref('#16a34a')
// Цвет брака / отмены — error из дизайн-системы Nuxt UI (`--ui-error`).
const errorColor = ref('#ef4444')

const probeColor = (css: string): string | null => {
  const probe = document.createElement('span')
  probe.style.color = css
  probe.style.display = 'none'
  document.body.appendChild(probe)
  const resolved = getComputedStyle(probe).color
  document.body.removeChild(probe)
  return resolved || null
}

onMounted(() => {
  const primary = probeColor('var(--ui-primary)')
  if (primary) primaryColor.value = primary
  const error = probeColor('var(--ui-error)')
  if (error) errorColor.value = error
})

// Терминальный статус брака / отмены — цель `rejected` во всех сущностях.
const isReject = (code: string): boolean => code === 'rejected'

// Иконка в центре узла — один <symbol> на код статуса. unovis выставляет
// width/height на <use>, поэтому иконки задаём как <symbol> с viewBox (у <g>
// нет размеров и масштабирование не работает). Иконка внутри узла — белая
// (currentColor у stroke иконок Lucide) поверх сплошной primary-заливки узла.
const svgDefs = Object.entries(FSM_ICON_BODIES)
  .map(
    ([code, body]) =>
      `<symbol id="fsm-ic-${code}" viewBox="0 0 24 24"><g style="color:#ffffff">${body}</g></symbol>`,
  )
  .join('')

type GraphNodeDatum = FsmNode & { id: string }
type GraphLinkDatum = FsmLink & { id: string }

const graphData = computed<{ nodes: GraphNodeDatum[]; links: GraphLinkDatum[] }>(() => ({
  nodes: fsm.value.nodes.map((node) => ({ ...node, id: node.code })),
  links: fsm.value.links.map((link) => ({ ...link, id: `${link.source}->${link.target}` })),
}))

// Широкая раскладка: большой ranksep растягивает цепочку по горизонтали
// (граф вписывается по ширине контейнера), nodesep разводит ветки по вертикали.
const dagreLayoutSettings = {
  rankdir: 'LR',
  ranksep: 220,
  nodesep: 80,
}

const fitViewPadding = { top: 48, right: 40, bottom: 48, left: 40 }

// Подпись узла — только код статуса, переведённый через i18n (statusLabels.*).
const nodeLabel = (node: GraphNodeDatum): string =>
  statusLabel(ENTITY_BY_KIND[props.kind], node.code)
const nodeIcon = (node: GraphNodeDatum): string => `#fsm-ic-${node.code}`
const nodeIconSize = (): number => 22
const nodeFill = (node: GraphNodeDatum): string =>
  isReject(node.code) ? errorColor.value : primaryColor.value
const nodeStroke = (node: GraphNodeDatum): string =>
  isReject(node.code) ? errorColor.value : primaryColor.value
const nodeSize = (): number => 44
const nodeStrokeWidth = (): number => 2

const linkArrow = () => 'single' as const
// Прямой ход — сплошная линия; возврат (loop) и брак/отклонение (reject) —
// пунктиром, чтобы визуально отличать их. Цвет у всех один — primary.
const linkStyle = (link: GraphLinkDatum) =>
  link.kind === 'forward' ? ('solid' as const) : ('dashed' as const)
// Переход в статус брака / отмены (reject) — error; остальные — primary.
const linkStroke = (link: GraphLinkDatum): string =>
  link.kind === 'reject' ? errorColor.value : primaryColor.value
const linkWidth = (): number => 2
// Поток анимируется по ВСЕМ рёбрам — схема показывает движение к терминальным
// статусам целиком, независимо от состояния конкретной записи.
const linkFlow = (): boolean => true
// Подпись показываем только у прямых/терминальных переходов. У петли (возврата)
// подпись опускаем: две встречные подписи между одной парой узлов накладывались.
const linkLabel = (link: GraphLinkDatum) =>
  link.kind === 'loop' ? undefined : { text: link.label }
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <p class="text-sm text-muted">
      {{ t('crud.statusFlowDescription') }}
    </p>

    <div class="status-fsm min-h-0 flex-1 overflow-hidden rounded-lg border border-default bg-elevated/30">
      <VisSingleContainer
        :key="primaryColor"
        class="h-full w-full"
        :data="graphData"
        :svg-defs="svgDefs"
      >
        <VisGraph
          layout-type="dagre"
          :dagre-layout-settings="dagreLayoutSettings"
          :fit-view-padding="fitViewPadding"
          :node-label="nodeLabel"
          :node-icon="nodeIcon"
          :node-icon-size="nodeIconSize"
          :node-fill="nodeFill"
          :node-size="nodeSize"
          :node-stroke="nodeStroke"
          :node-stroke-width="nodeStrokeWidth"
          :node-label-trim="false"
          :link-arrow="linkArrow"
          :link-style="linkStyle"
          :link-stroke="linkStroke"
          :link-width="linkWidth"
          :link-flow="linkFlow"
          :link-curvature="1"
          :link-label="linkLabel"
          :link-neighbor-spacing="28"
          :link-flow-particle-size="3"
          :link-flow-particle-speed="18"
        />
      </VisSingleContainer>
    </div>
  </div>
</template>

<style scoped>
.status-fsm {
  /* Шрифт графа наследуется из шрифта приложения. */
  --vis-font-family: inherit;
  --vis-graph-node-label-font-family: inherit;
  --vis-graph-node-label-text-color: var(--ui-text-highlighted);
  /* Подложка подписи узла — под тёмную тему, как у подписей на рёбрах. */
  --vis-graph-node-label-background: var(--ui-bg-elevated);
  --vis-graph-node-sublabel-text-color: var(--ui-text-muted);
  --vis-graph-link-label-text-color: var(--ui-text-muted);
  --vis-graph-link-label-background: var(--ui-bg-elevated);
}
/* unovis-контейнер должен занять всю высоту/ширину родителя. */
.status-fsm > :deep(div) {
  height: 100%;
  width: 100%;
}
</style>
