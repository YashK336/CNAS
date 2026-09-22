import '@xyflow/react/dist/style.css'

import { Maximize2 } from 'lucide-react'
import { useCallback, useMemo } from 'react'
import {
  Background,
  BackgroundVariant,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react'
import type { FitViewOptions } from '@xyflow/react'

import type { EntityGraphNode } from '@/components/network/GraphNodes'
import {
  GRAPH_EDGE_TYPES,
  GRAPH_NODE_TYPES,
} from '@/components/network/graphElementTypes'
import type { RelationshipEdgeType } from '@/components/network/RelationshipEdge'
import { NODE_SIZE } from '@/lib/graph'
import { graphSurfaceFor } from '@/lib/chartTheme'
import type { GraphView } from '@/types'
import { useTheme } from '@/hooks/useTheme'

const FIT_OPTIONS: FitViewOptions = { padding: 0.16, duration: 300 }

export interface PersonNetworkCanvasProps {
  view: GraphView
  onSelectEntity: (entityId: string) => void
}

/**
 * Read-only local neighbourhood canvas. Shares the explorer's node and edge
 * renderers so the two surfaces stay visually identical, but carries no
 * filters, minimap or tracing — this is context, not a second explorer.
 */
function LocalCanvas({ view, onSelectEntity }: PersonNetworkCanvasProps) {
  const { fitView } = useReactFlow()
  const { theme } = useTheme()
  const graphSurface = graphSurfaceFor(theme)

  const nodes = useMemo<EntityGraphNode[]>(
    () =>
      view.nodes.map((node) => {
        const size = node.size ?? NODE_SIZE[node.entity.entity_type]

        return {
          id: node.id,
          type: node.entity.entity_type,
          position: node.position,
          data: { view: node },
          width: size.width,
          height: size.height,
          style: { width: size.width, height: size.height },
          zIndex: node.selected ? 20 : 1,
        }
      }),
    [view.nodes],
  )

  const edges = useMemo<RelationshipEdgeType[]>(
    () =>
      view.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: 'relationship',
        interactionWidth: 10,
        data: {
          relationship: edge.relationship,
          count: edge.count,
          curveOffset: edge.curveOffset,
          emphasis: edge.emphasis,
          showLabel: edge.showLabel,
        },
      })),
    [view.edges],
  )

  const handleFit = useCallback(() => {
    void fitView(FIT_OPTIONS)
  }, [fitView])

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={GRAPH_NODE_TYPES}
        edgeTypes={GRAPH_EDGE_TYPES}
        colorMode={theme}
        fitView
        fitViewOptions={FIT_OPTIONS}
        minZoom={0.15}
        maxZoom={2}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        elementsSelectable={false}
        zoomOnDoubleClick={false}
        attributionPosition="bottom-left"
        onNodeClick={(_, node) => onSelectEntity(node.id)}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={22}
          size={1}
          color={graphSurface.dot}
        />
      </ReactFlow>

      <button
        type="button"
        title="Fit view"
        aria-label="Fit view"
        onClick={handleFit}
        className="absolute top-2 right-2 z-10 inline-flex h-7 w-7 items-center justify-center rounded-sm border border-line bg-surface/95 text-ink-muted hover:bg-surface-hover hover:text-ink"
      >
        <Maximize2 size={13} strokeWidth={1.75} />
      </button>
    </div>
  )
}

export function PersonNetworkCanvas(props: PersonNetworkCanvasProps) {
  return (
    <ReactFlowProvider>
      <LocalCanvas {...props} />
    </ReactFlowProvider>
  )
}
