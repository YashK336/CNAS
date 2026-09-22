import { Car, Cctv, ScrollText, User } from 'lucide-react'
import { memo } from 'react'
import { Handle, Position, useViewport } from '@xyflow/react'
import type { Node, NodeProps } from '@xyflow/react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'
import type { EntityType, GraphViewNode } from '@/types'

/** Type aliases (not interfaces) so React Flow's `Record` bound is satisfied. */
export type GraphNodeData = { view: GraphViewNode }
export type EntityGraphNode = Node<GraphNodeData, EntityType>

const TONE: Record<EntityType, { idle: string; icon: string }> = {
  person: {
    idle: 'border-line-strong bg-surface-raised',
    icon: 'text-accent',
  },
  vehicle: {
    idle: 'border-line bg-surface',
    icon: 'text-ink-faint',
  },
  crime_event: {
    idle: 'border-signal-critical/30 bg-signal-critical/8',
    icon: 'text-signal-critical',
  },
  surveillance_event: {
    idle: 'border-signal-medium/25 bg-signal-medium/8',
    icon: 'text-signal-medium',
  },
}

const CENTER_HANDLE = {
  left: '50%',
  top: '50%',
  width: 1,
  height: 1,
  minWidth: 1,
  minHeight: 1,
  border: 'none',
  background: 'transparent',
  opacity: 0,
  transform: 'translate(-50%, -50%)',
} as const

function clipName(name: string, maxChars: number): string {
  const trimmed = name.trim()
  if (trimmed.length <= maxChars) return trimmed
  return `${trimmed.slice(0, Math.max(1, maxChars - 1)).trimEnd()}…`
}

function labelVisible(
  view: GraphViewNode,
  zoom: number,
): boolean {
  if (view.selected) return true
  if (view.labelPriority === 'always') return true
  if (view.labelPriority === 'zoom') return zoom >= 0.62
  return zoom >= 1.05
}

function nameBudget(view: GraphViewNode, zoom: number): number {
  if (view.selected) return zoom >= 0.95 ? 36 : 22
  if (zoom >= 1.25) return 28
  if (zoom >= 0.95) return 18
  if (zoom >= 0.7) return 12
  return 9
}

function labelMaxWidth(zoom: number, selected: boolean): number {
  if (selected) return zoom >= 0.95 ? 168 : 112
  if (zoom >= 1.25) return 148
  if (zoom >= 0.95) return 108
  if (zoom >= 0.7) return 76
  return 58
}

interface EntityNodeShellProps {
  view: GraphViewNode
  icon: ReactNode
}

function EntityNodeShell({ view, icon }: EntityNodeShellProps) {
  const { zoom } = useViewport()
  const tone = TONE[view.entity.entity_type]
  const isEndpoint = view.pathRole === 'source' || view.pathRole === 'target'
  const showLabel = labelVisible(view, zoom)
  const displayName = clipName(view.primary, nameBudget(view, zoom))
  const showSecondary = Boolean(view.secondary) && (view.selected || isEndpoint)
  const labelOnLeft = view.position.x + view.size.width / 2 < 0
  const glyph = view.size.width <= 32

  return (
    <div
      title={view.primary}
      className={cn(
        'relative h-full w-full',
        glyph ? 'overflow-visible' : 'overflow-hidden',
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={false}
        style={CENTER_HANDLE}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={false}
        style={CENTER_HANDLE}
      />

      <div
        className={cn(
          'flex h-full w-full items-center border',
          glyph
            ? 'justify-center rounded-full'
            : 'gap-1 rounded-sm pr-1.5 pl-1',
          tone.idle,
          view.inCommunity && 'border-accent bg-accent/25',
          view.inNeighborhood && 'border-accent/45 bg-accent/10',
          view.pathRole !== null && 'border-accent/70 bg-accent-muted',
          isEndpoint && 'border-accent bg-accent/20',
          view.selected && 'border-accent bg-accent/20 ring-2 ring-accent/80',
          view.dimmed && 'opacity-18',
        )}
      >
        <span aria-hidden className={cn('shrink-0', tone.icon)}>
          {icon}
        </span>
        {!glyph && showLabel ? (
          <span className="min-w-0 flex-1 leading-none">
            <span className="block truncate text-[10px] font-medium text-ink">
              {displayName}
            </span>
            {showSecondary ? (
              <span className="mt-[2px] block truncate font-mono text-[9px] text-ink-faint">
                {view.secondary}
              </span>
            ) : null}
          </span>
        ) : null}
      </div>

      {glyph && showLabel ? (
        <span
          className={cn(
            'pointer-events-none absolute top-1/2 z-10 -translate-y-1/2 leading-none',
            labelOnLeft ? 'right-full mr-1 text-right' : 'left-full ml-1',
          )}
          style={{ maxWidth: labelMaxWidth(zoom, view.selected) }}
        >
          <span
            className={cn(
              'block truncate text-ink',
              view.selected ? 'text-[11px] font-semibold' : 'text-[10px] font-medium',
            )}
          >
            {displayName}
          </span>
          {showSecondary ? (
            <span className="mt-[2px] block truncate font-mono text-[9px] text-ink-faint">
              {view.secondary}
            </span>
          ) : null}
        </span>
      ) : null}

      {!showLabel ? <span className="sr-only">{view.primary}</span> : null}

      {isEndpoint ? (
        <span className="absolute -top-[14px] left-1/2 -translate-x-1/2 rounded-sm border border-accent/50 bg-canvas px-1 text-[9px] leading-[13px] font-semibold tracking-widest text-accent uppercase">
          {view.pathRole}
        </span>
      ) : null}
    </div>
  )
}

const ICON_PROPS = { strokeWidth: 1.75 } as const

export const PersonGraphNode = memo(function PersonGraphNode({
  data,
}: NodeProps<EntityGraphNode>) {
  return (
    <EntityNodeShell
      view={data.view}
      icon={<User size={11} {...ICON_PROPS} />}
    />
  )
})

export const VehicleGraphNode = memo(function VehicleGraphNode({
  data,
}: NodeProps<EntityGraphNode>) {
  return (
    <EntityNodeShell view={data.view} icon={<Car size={10} {...ICON_PROPS} />} />
  )
})

export const CrimeEventGraphNode = memo(function CrimeEventGraphNode({
  data,
}: NodeProps<EntityGraphNode>) {
  return (
    <EntityNodeShell
      view={data.view}
      icon={<ScrollText size={10} {...ICON_PROPS} />}
    />
  )
})

export const SurveillanceGraphNode = memo(function SurveillanceGraphNode({
  data,
}: NodeProps<EntityGraphNode>) {
  return (
    <EntityNodeShell
      view={data.view}
      icon={<Cctv size={10} {...ICON_PROPS} />}
    />
  )
})
