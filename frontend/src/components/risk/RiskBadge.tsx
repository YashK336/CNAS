import { Badge } from '@/components/ui'
import type { BadgeTone } from '@/components/ui'
import { RISK_LEVEL_PRESENTATION } from '@/lib/risk'
import type { RiskLevel } from '@/types'

const TONE_BY_LEVEL: Record<RiskLevel, BadgeTone> = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
}

export interface RiskBadgeProps {
  level: RiskLevel
  /** Appends the 0-100 score, e.g. "High · 72". */
  score?: number
  className?: string
}

export function RiskBadge({ level, score, className }: RiskBadgeProps) {
  const presentation = RISK_LEVEL_PRESENTATION[level]

  return (
    <Badge tone={TONE_BY_LEVEL[level]} className={className}>
      <span className="tracking-wide uppercase">{presentation.label}</span>
      {score === undefined ? null : (
        <span className="font-mono tabular-nums opacity-80">{score}</span>
      )}
    </Badge>
  )
}
