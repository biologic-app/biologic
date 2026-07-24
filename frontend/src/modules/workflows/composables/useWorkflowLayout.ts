// composables/useWorkflowLayout.ts
// Авто-раскладка канваса сверху-вниз (dagre), эталон — официальный пример Vue Flow.
import type { JournalEdge, JournalNode } from '@/modules/workflows/types/journal'
import dagre from '@dagrejs/dagre'
import { Position, useVueFlow } from '@vue-flow/core'

const DEFAULT_WIDTH = 260
const DEFAULT_HEIGHT = 96

export function useWorkflowLayout() {
  const { findNode } = useVueFlow()

  function layout(nodes: JournalNode[], edges: JournalEdge[]): JournalNode[] {
    const g = new dagre.graphlib.Graph()
    g.setDefaultEdgeLabel(() => ({}))
    g.setGraph({ rankdir: 'TB', ranksep: 60, nodesep: 40 })

    for (const node of nodes) {
      const dimensions = findNode(node.id)?.dimensions
      g.setNode(node.id, {
        width: dimensions?.width || DEFAULT_WIDTH,
        height: dimensions?.height || DEFAULT_HEIGHT,
      })
    }
    for (const edge of edges) {
      g.setEdge(edge.source, edge.target)
    }

    dagre.layout(g)

    return nodes.map((node) => {
      const position = g.node(node.id)
      return {
        ...node,
        targetPosition: Position.Top,
        sourcePosition: Position.Bottom,
        position: { x: position.x - (position.width ?? DEFAULT_WIDTH) / 2, y: position.y - (position.height ?? DEFAULT_HEIGHT) / 2 },
      }
    })
  }

  return { layout }
}
