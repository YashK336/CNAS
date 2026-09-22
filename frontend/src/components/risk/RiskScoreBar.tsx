import { cn } from '@/lib/cn'
import { RISK_LEVEL_PRESENTATION, riskLevelFromScore } from '@/lib/risk'
import type { RiskLevel } from '@/types'

export interface RiskScoreBarProps {
  /** Rule-engine score, 0-100. */
  score: number
  /** Defaults to the backend threshold mapping for the given score. */
  level?: RiskLevel
  className?: string
}

/** Compact 0-100 meter for use inside dense table rows. */
export function RiskScoreBar({ score, level, className }: RiskScoreBarProps) {
  const safeScore = Number.isFinite(score)
    ? Math.min(100, Math.max(0, score))
    : 0
  const resolvedLevel = level ?? riskLevelFromScore(safeScore)

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className="h-1 w-full min-w-16 overflow-hidden rounded-sm bg-surface-active"
        role="meter"
        aria-valuenow={safeScore}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Risk score"
      >
        <div
          className={cn(
            'h-full rounded-sm',
            RISK_LEVEL_PRESENTATION[resolvedLevel].barClass,
          )}
          style={{ width: `${safeScore}%` }}
        />
      </div>
      <span className="w-6 shrink-0 text-right font-mono text-2xs text-ink-muted tabular-nums">
        {safeScore}
      </span>
    </div>
  )
}
