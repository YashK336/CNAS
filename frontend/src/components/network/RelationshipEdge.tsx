import { memo } from 'react'
import { EdgeLabelRenderer } from '@xyflow/react'
import type { Edge, EdgeProps } from '@xyflow/react'

import { formatNumber } from '@/lib/format'
import type { EdgeEmphasis } from '@/types'

export type RelationshipEdgeData = {
  relationship: string
  count: number
  curveOffset: number
  emphasis: EdgeEmphasis
  showLabel: boolean
}

export type RelationshipEdgeType = Edge<RelationshipEdgeData, 'relationship'>

const STROKE_CLASS: Record<EdgeEmphasis, string> = {
  normal: 'stroke-line',
  dimmed: 'stroke-line',
  active: 'stroke-accent',
}

const STROKE_WIDTH: Record<EdgeEmphasis, number> = {
  normal: 1,
  dimmed: 1,
  active: 1.75,
}

const STROKE_OPACITY: Record<EdgeEmphasis, number> = {
  normal: 0.28,
  dimmed: 0.05,
  active: 1,
}

/**
 * Straight connector between two entity centres, bowed out when several
 * relationships (or both directions) share the same pair so each stays
 * individually visible and clickable. Relationship labels appear only while an
 * edge is emphasised, otherwise thousands of labels would cover the canvas.
 */
export const RelationshipEdge = memo(function RelationshipEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
  markerEnd,
  interactionWidth,
}: EdgeProps<RelationshipEdgeType>) {
  const emphasis = data?.emphasis ?? 'normal'
  const offset = data?.curveOffset ?? 0

  const midX = (sourceX + targetX) / 2
  const midY = (sourceY + targetY) / 2

  let controlX = midX
  let controlY = midY

  if (offset !== 0) {
    const dx = targetX - sourceX
    const dy = targetY - sourceY
    const length = Math.hypot(dx, dy) || 1
    controlX = midX + (-dy / length) * offset
    controlY = midY + (dx / length) * offset
  }

  const path =
    offset === 0
      ? `M ${sourceX},${sourceY} L ${targetX},${targetY}`
      : `M ${sourceX},${sourceY} Q ${controlX},${controlY} ${targetX},${targetY}`

  // Midpoint of the quadratic curve, where the label sits.
  const labelX = (sourceX + 2 * controlX + targetX) / 4
  const labelY = (sourceY + 2 * controlY + targetY) / 4

  return (
    <>
      <path
        d={path}
        fill="none"
        markerEnd={markerEnd}
        strokeWidth={STROKE_WIDTH[emphasis]}
        strokeOpacity={STROKE_OPACITY[emphasis]}
        // Keeps links hairline-thin at every zoom level instead of thickening
        // with the viewport transform.
        vectorEffect="non-scaling-stroke"
        className={STROKE_CLASS[emphasis]}
      />

      <path
        d={path}
        fill="none"
        stroke="transparent"
        strokeWidth={interactionWidth ?? 12}
        className="react-flow__edge-interaction"
      />

      {data?.showLabel ? (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan pointer-events-none absolute flex items-center gap-1 rounded-sm border border-accent/40 bg-canvas px-1 py-[1px] font-mono text-[9px] leading-[13px] tracking-wide text-accent"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            {data.relationship}
            {data.count > 1 ? (
              <span className="text-ink-faint">
                ×{formatNumber(data.count)}
              </span>
            ) : null}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  )
})
