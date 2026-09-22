import { useMemo, useState } from 'react'

import { LandingContainer } from './LandingContainer'
import { LandingSection } from './LandingSection'
import { RevealOnScroll } from './RevealOnScroll'
import { SectionHeading } from './SectionHeading'

type NodeShape = 'circle' | 'square' | 'diamond'

interface DemoNode {
  id: string
  x: number
  y: number
  shape: NodeShape
  label: string
  sublabel: string
  emphasis?: boolean
}

interface DemoEdge {
  from: string
  to: string
  label: string
  dashed?: boolean
  curved?: boolean
}

const NODES: DemoNode[] = [
  { id: 'case', x: 360, y: 52, shape: 'diamond', label: 'FIR-2024-0182', sublabel: 'Case', emphasis: true },
  { id: 'personA', x: 168, y: 158, shape: 'circle', label: 'P104', sublabel: 'Person' },
  { id: 'personB', x: 552, y: 158, shape: 'circle', label: 'P217', sublabel: 'Person' },
  { id: 'phoneA', x: 88, y: 272, shape: 'square', label: '+91 •••• 0142', sublabel: 'Phone' },
  { id: 'vehicleA', x: 250, y: 306, shape: 'square', label: 'DL •• AB ••41', sublabel: 'Vehicle' },
  { id: 'accountB', x: 632, y: 272, shape: 'square', label: 'ACC •••• 2290', sublabel: 'Account' },
  { id: 'location', x: 360, y: 344, shape: 'diamond', label: 'Sector 21', sublabel: 'Location' },
]

const EDGES: DemoEdge[] = [
  { from: 'case', to: 'personA', label: 'INVOLVED_IN' },
  { from: 'case', to: 'personB', label: 'INVOLVED_IN' },
  { from: 'case', to: 'location', label: 'AT_LOCATION' },
  { from: 'personA', to: 'phoneA', label: 'HAS_PHONE' },
  { from: 'personA', to: 'vehicleA', label: 'OWNS' },
  { from: 'personB', to: 'accountB', label: 'HAS_ACCOUNT' },
  { from: 'personA', to: 'personB', label: 'CALLED', curved: true },
  { from: 'personA', to: 'location', label: 'PRESENT_AT', dashed: true },
]

const NODE_LOOKUP = new Map(NODES.map((node) => [node.id, node]))

function NodeGlyph({
  node,
  active,
  dimmed,
}: {
  node: DemoNode
  active: boolean
  dimmed: boolean
}) {
  const size = (node.shape === 'circle' ? 15 : 12) * (active ? 1.12 : 1)
  const fill = node.emphasis || active ? 'fill-accent/22' : 'fill-surface-raised'
  const stroke = node.emphasis || active ? 'stroke-accent' : 'stroke-line-strong'
  const opacity = dimmed ? 0.32 : 1

  const shared = {
    className: `${fill} ${stroke} transition-[opacity,transform] duration-200`,
    strokeWidth: active ? 2 : 1.5,
    style: { opacity },
  }

  if (node.shape === 'circle') {
    return <circle r={size} {...shared} />
  }

  if (node.shape === 'diamond') {
    return (
      <rect
        x={-size}
        y={-size}
        width={size * 2}
        height={size * 2}
        transform="rotate(45)"
        {...shared}
      />
    )
  }

  return <rect x={-size} y={-size} width={size * 2} height={size * 2} rx={3} {...shared} />
}

function EdgePath({
  edge,
  highlighted,
  dimmed,
}: {
  edge: DemoEdge
  highlighted: boolean
  dimmed: boolean
}) {
  const from = NODE_LOOKUP.get(edge.from)
  const to = NODE_LOOKUP.get(edge.to)
  if (!from || !to) return null

  const midX = (from.x + to.x) / 2
  const midY = (from.y + to.y) / 2
  const path = edge.curved
    ? `M ${from.x} ${from.y} Q ${midX} ${midY - 46} ${to.x} ${to.y}`
    : `M ${from.x} ${from.y} L ${to.x} ${to.y}`
  const labelY = edge.curved ? midY - 46 : midY

  return (
    <g style={{ opacity: dimmed ? 0.22 : 1, transition: 'opacity 200ms ease' }}>
      <path
        d={path}
        fill="none"
        className={highlighted ? 'stroke-accent/80' : 'stroke-ink-faint/45'}
        strokeWidth={highlighted ? 1.75 : 1.25}
        strokeDasharray={edge.dashed ? '4 4' : edge.curved ? '3 5' : undefined}
        style={{ transition: 'stroke 200ms ease, stroke-width 200ms ease' }}
      />
      {edge.curved ? (
        <path
          d={path}
          fill="none"
          className="stroke-accent/70 motion-safe:animate-[cnas-flow_1.8s_linear_infinite]"
          strokeWidth={1.25}
          strokeDasharray="3 5"
        />
      ) : null}
      <g transform={`translate(${midX}, ${labelY})`}>
        <rect
          x={-edge.label.length * 3.1 - 6}
          y={-8}
          width={edge.label.length * 6.2 + 12}
          height={16}
          rx={3}
          className={highlighted ? 'fill-canvas stroke-accent/60' : 'fill-canvas stroke-line-strong'}
          strokeWidth={1}
        />
        <text
          textAnchor="middle"
          dominantBaseline="middle"
          className={highlighted ? 'fill-ink font-mono' : 'fill-ink-faint font-mono'}
          style={{ fontSize: 8.5, letterSpacing: '0.02em' }}
        >
          {edge.label}
        </text>
      </g>
    </g>
  )
}

export function IntelligenceVisualizationSection() {
  const [activeNode, setActiveNode] = useState<string | null>(null)

  const connectedNodeIds = useMemo(() => {
    if (!activeNode) return null
    const ids = new Set<string>([activeNode])
    for (const edge of EDGES) {
      if (edge.from === activeNode) ids.add(edge.to)
      if (edge.to === activeNode) ids.add(edge.from)
    }
    return ids
  }, [activeNode])

  return (
    <LandingSection
      id="visualization"
      intensity={0.6}
      tint="bg-canvas/50"
      className="scroll-mt-20 border-b border-line/70 py-20 sm:py-24"
    >
      <LandingContainer className="relative">
        <RevealOnScroll>
          <SectionHeading
            eyebrow="Knowledge graph"
            title="One resolved graph, viewed from every angle"
            description="A single FIR touches several entity types at once. CNAS resolves each mention and renders the result as a connected, explorable graph — this panel is a static illustration of that shape, not a live query. Hover or select a node to trace its connections."
          />
        </RevealOnScroll>

        <RevealOnScroll delayMs={100}>
          <div className="relative mt-12 overflow-hidden rounded-2xl border border-line bg-surface">
            <div className="grid-texture absolute inset-0 opacity-60" aria-hidden />

            <div className="relative flex items-center justify-between gap-3 border-b border-line/70 px-4 py-3">
              <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
                Sample case graph
              </p>
              <span className="rounded-sm border border-line-strong bg-surface-raised px-1.5 py-0.5 text-2xs text-ink-faint">
                Illustrative · synthetic data
              </span>
            </div>

            <svg
              viewBox="0 0 720 400"
              className="relative h-auto w-full"
              role="img"
              aria-label="Illustrative diagram of one FIR case resolving to two persons, a phone, a vehicle, a bank account, and a location, connected by CNAS relationship types. Nodes highlight their connections on hover."
              onMouseLeave={() => setActiveNode(null)}
            >
              {EDGES.map((edge) => {
                const highlighted =
                  activeNode !== null &&
                  (edge.from === activeNode || edge.to === activeNode)
                const dimmed = connectedNodeIds !== null && !highlighted
                return (
                  <EdgePath
                    key={`${edge.from}-${edge.to}`}
                    edge={edge}
                    highlighted={highlighted}
                    dimmed={dimmed}
                  />
                )
              })}
              {NODES.map((node) => {
                const isActive = activeNode === node.id
                const dimmed = connectedNodeIds !== null && !connectedNodeIds.has(node.id)
                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    onMouseEnter={() => setActiveNode(node.id)}
                    onFocus={() => setActiveNode(node.id)}
                    onClick={() => setActiveNode((current) => (current === node.id ? null : node.id))}
                    tabIndex={0}
                    role="button"
                    aria-pressed={isActive}
                    aria-label={`${node.label} — ${node.sublabel}`}
                    className="cursor-pointer outline-none"
                  >
                    <NodeGlyph node={node} active={isActive} dimmed={dimmed} />
                    <text
                      y={node.shape === 'circle' ? 30 : 26}
                      textAnchor="middle"
                      className="fill-ink"
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        opacity: dimmed ? 0.35 : 1,
                        transition: 'opacity 200ms ease',
                      }}
                    >
                      {node.label}
                    </text>
                    <text
                      y={node.shape === 'circle' ? 43 : 39}
                      textAnchor="middle"
                      className="fill-ink-faint"
                      style={{
                        fontSize: 9,
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        opacity: dimmed ? 0.35 : 1,
                        transition: 'opacity 200ms ease',
                      }}
                    >
                      {node.sublabel}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        </RevealOnScroll>
      </LandingContainer>
    </LandingSection>
  )
}
