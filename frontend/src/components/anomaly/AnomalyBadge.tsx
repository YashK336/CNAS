import { Badge } from '@/components/ui'
import type { BadgeTone } from '@/components/ui'
import { ANOMALY_LEVEL_PRESENTATION } from '@/lib/anomaly'
import type { AnomalyLevel } from '@/types'

const TONE_BY_LEVEL: Record<AnomalyLevel, BadgeTone> = {
  NORMAL: 'low',
  ELEVATED: 'medium',
  HIGH: 'high',
  EXTREME: 'critical',
}

export interface AnomalyBadgeProps {
  level: AnomalyLevel
  score?: number
  className?: string
}

export function AnomalyBadge({ level, score, className }: AnomalyBadgeProps) {
  const presentation = ANOMALY_LEVEL_PRESENTATION[level]

  return (
    <Badge tone={TONE_BY_LEVEL[level]} className={className}>
      <span className="tracking-wide uppercase">{presentation.label}</span>
      {score === undefined ? null : (
        <span className="font-mono tabular-nums opacity-80">{score}</span>
      )}
    </Badge>
  )
}
