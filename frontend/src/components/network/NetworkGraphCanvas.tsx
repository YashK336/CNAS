import '@xyflow/react/dist/style.css'

import {
  Crosshair,
  Maximize2,
  RotateCcw,
  Route,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef } from 'react'
import {
  Background,
  BackgroundVariant,
  MarkerType,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react'
import type { FitViewOptions, Node } from '@xyflow/react'
import type { ReactNode } from 'react'

import { CHART_COLORS, ENTITY_HEX, chartColorsFor, graphSurfaceFor } from '@/lib/chartTheme'
import type { EntityType, GraphView } from '@/types'
import { useTheme } from '@/hooks/useTheme'
import type { EntityGraphNode } from './GraphNodes'
import { GRAPH_EDGE_TYPES, GRAPH_NODE_TYPES } from './graphElementTypes'
import type { RelationshipEdgeType } from './RelationshipEdge'

/** Imperative viewport request from the page; `token` triggers the effect. */
export interface ViewportCommand {
  token: number
  kind: 'fit' | 'nodes' | 'center'
  /** Targets for `nodes` and `center`. */
  ids: string[]
}

export interface NetworkGraphCanvasProps {
  view: GraphView
  viewport: ViewportCommand
  onSelectNode: (nodeId: string) => void
  onSelectEdge: (edgeId: string) => void
  onClearSelection: () => void
  onClearPath: () => void
  onResetFilters: () => void
  canClearSelection: boolean
  canClearPath: boolean
  canResetFilters: boolean
  exploreHops: 1 | 2 | 3
  exploreActive: boolean
  onExploreHopsChange: (hops: 1 | 2 | 3) => void
  onResetOverview: () => void
}

const FIT_OPTIONS: FitViewOptions = {
  padding: 0.16,
  duration: 320,
  maxZoom: 1.05,
  minZoom: 0.08,
}
const MINIMAP_SIZE = { width: 176, height: 112 }

function minimapNodeColor(node: Node): string {
  const type = node.type as EntityType | undefined
  return type ? ENTITY_HEX[type] : CHART_COLORS.axis
}

interface ToolButtonProps {
  label: string
  icon: ReactNode
  onClick: () => void
  disabled?: boolean
}

function ToolButton({ label, icon, onClick, disabled = false }: ToolButtonProps) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className="inline-flex h-7 w-7 items-center justify-center rounded-sm border border-transparent text-ink-muted hover:bg-surface-hover hover:text-ink disabled:pointer-events-none disabled:opacity-35"
    >
      {icon}
    </button>
  )
}

function GraphCanvas({
  view,
  viewport,
  onSelectNode,
  onSelectEdge,
  onClearSelection,
  onClearPath,
  onResetFilters,
  canClearSelection,
  canClearPath,
  canResetFilters,
  exploreHops,
  exploreActive,
  onExploreHopsChange,
  onResetOverview,
}: NetworkGraphCanvasProps) {
  const { fitView, setCenter, zoomIn, zoomOut } = useReactFlow()
  const { theme } = useTheme()
  const chartColors = chartColorsFor(theme)
  const graphSurface = graphSurfaceFor(theme)

  const nodes = useMemo<EntityGraphNode[]>(
    () =>
      view.nodes.map((node) => {
        const size = node.size

        return {
          id: node.id,
          type: node.entity.entity_type,
          position: node.position,
          data: { view: node },
          // Supplying measurements up front avoids a measure pass per node.
          width: size.width,
          height: size.height,
          style: { width: size.width, height: size.height, overflow: 'visible' },
          className: '!overflow-visible',
          zIndex:
            node.selected || node.pathRole !== null || node.inNeighborhood
              ? 20
              : 1,
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
        zIndex: edge.emphasis === 'active' ? 10 : 0,
        data: {
          relationship: edge.relationship,
          count: edge.count,
          curveOffset: edge.curveOffset,
          emphasis: edge.emphasis,
          showLabel: edge.showLabel,
        },
        // Arrowheads only where direction matters, otherwise thousands of
        // markers would bury the canvas.
        ...(edge.emphasis === 'active'
          ? {
              markerEnd: {
                type: MarkerType.ArrowClosed,
                width: 13,
                height: 13,
                color: chartColors.accent,
              },
            }
          : {}),
      })),
    [view.edges, chartColors.accent],
  )

  const positionsById = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>()
    for (const node of view.nodes) {
      const size = node.size
      map.set(node.id, {
        x: node.position.x + size.width / 2,
        y: node.position.y + size.height / 2,
      })
    }
    return map
  }, [view.nodes])

  const { token, kind, ids } = viewport
  const handledTokenRef = useRef(0)

  useEffect(() => {
    // Only act on a fresh command. `positionsById` changes on every selection,
    // and the camera must not move for that.
    if (token === 0 || handledTokenRef.current === token) return
    handledTokenRef.current = token

    // Wait for React Flow to commit the new node set before moving the camera.
    let inner = 0
    const frame = requestAnimationFrame(() => {
      inner = requestAnimationFrame(() => {
        if (kind === 'center') {
          const target = ids[0] ? positionsById.get(ids[0]) : undefined
          if (target) {
            void setCenter(target.x, target.y, { zoom: 1.15, duration: 360 })
          }
          return
        }

        if (kind === 'nodes' && ids.length > 0) {
          void fitView({
            padding: 0.32,
            duration: 380,
            maxZoom: 1.35,
            nodes: ids.map((id) => ({ id })),
          })
          return
        }

        void fitView(FIT_OPTIONS)
      })
    })

    return () => {
      cancelAnimationFrame(frame)
      cancelAnimationFrame(inner)
    }
  }, [token, kind, ids, fitView, setCenter, positionsById])

  const handleFit = useCallback(() => {
    requestAnimationFrame(() => {
      void fitView(FIT_OPTIONS)
    })
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
        minZoom={0.08}
        maxZoom={2.5}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        elementsSelectable={false}
        zoomOnDoubleClick={false}
        onlyRenderVisibleElements
        attributionPosition="bottom-left"
        onNodeClick={(_, node) => onSelectNode(node.id)}
        onEdgeClick={(_, edge) => onSelectEdge(edge.id)}
        onPaneClick={onClearSelection}
        onDoubleClick={(event) => {
          const target = event.target as HTMLElement
          if (
            target.classList.contains('react-flow__pane') ||
            target.closest('.react-flow__background')
          ) {
            handleFit()
          }
        }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={26}
          size={1}
          color={graphSurface.dot}
        />
        <MiniMap
          pannable
          zoomable
          ariaLabel="Network overview"
          maskColor={graphSurface.minimapMask}
          nodeColor={minimapNodeColor}
          nodeStrokeWidth={0}
          // React Flow reads the SVG size from `style`, not from CSS classes.
          style={MINIMAP_SIZE}
          className="!right-3 !bottom-3 !m-0 !rounded-sm !border !border-line !bg-surface max-xl:!hidden"
        />
      </ReactFlow>

      <div className="absolute top-3 left-3 z-10 flex items-center gap-0.5 rounded-sm border border-line bg-surface/95 p-1">
        <button
          type="button"
          title="Reset to overview"
          aria-pressed={!exploreActive}
          onClick={onResetOverview}
          className={`h-7 rounded-sm px-2 text-[10px] font-semibold ${
            exploreActive
              ? 'text-ink-muted hover:bg-surface-hover hover:text-ink'
              : 'bg-accent/15 text-accent'
          }`}
        >
          Overview
        </button>
        {([1, 2, 3] as const).map((hops) => (
          <button
            key={hops}
            type="button"
            title={`Show ${hops}-hop neighbourhood`}
            aria-pressed={exploreActive && exploreHops === hops}
            disabled={!exploreActive}
            onClick={() => onExploreHopsChange(hops)}
            className={`h-7 rounded-sm px-2 text-[10px] font-semibold disabled:pointer-events-none disabled:opacity-35 ${
              exploreActive && exploreHops === hops
                ? 'bg-accent/15 text-accent'
                : 'text-ink-muted hover:bg-surface-hover hover:text-ink'
            }`}
          >
            {hops}-hop
          </button>
        ))}
      </div>

      <div className="absolute top-3 right-3 z-10 flex items-center gap-0.5 rounded-sm border border-line bg-surface/95 p-1">
        <ToolButton
          label="Reset view"
          icon={<Maximize2 size={13} strokeWidth={1.75} />}
          onClick={handleFit}
        />
        <ToolButton
          label="Zoom in"
          icon={<ZoomIn size={13} strokeWidth={1.75} />}
          onClick={() => void zoomIn({ duration: 180 })}
        />
        <ToolButton
          label="Zoom out"
          icon={<ZoomOut size={13} strokeWidth={1.75} />}
          onClick={() => void zoomOut({ duration: 180 })}
        />

        <span aria-hidden className="mx-0.5 h-4 w-px bg-line" />

        <ToolButton
          label="Clear selection"
          icon={<Crosshair size={13} strokeWidth={1.75} />}
          onClick={onClearSelection}
          disabled={!canClearSelection}
        />
        <ToolButton
          label="Clear path"
          icon={<Route size={13} strokeWidth={1.75} />}
          onClick={onClearPath}
          disabled={!canClearPath}
        />
        <ToolButton
          label="Reset filters"
          icon={<RotateCcw size={13} strokeWidth={1.75} />}
          onClick={onResetFilters}
          disabled={!canResetFilters}
        />
      </div>
    </div>
  )
}

/** React Flow needs its provider above any component calling `useReactFlow`. */
export function NetworkGraphCanvas(props: NetworkGraphCanvasProps) {
  return (
    <ReactFlowProvider>
      <GraphCanvas {...props} />
    </ReactFlowProvider>
  )
}
