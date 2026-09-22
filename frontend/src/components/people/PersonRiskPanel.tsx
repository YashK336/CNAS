import { ShieldAlert } from 'lucide-react'

import { RiskBadge, RiskScoreBar } from '@/components/risk'
import {
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { RISK_SIGNAL_LABELS } from '@/lib/risk'
import type { RiskProfile, RiskSignalScores } from '@/types'

const SIGNAL_KEYS = Object.keys(
  RISK_SIGNAL_LABELS,
) as (keyof RiskSignalScores)[]

export interface PersonRiskPanelProps {
  /** Null when the rule engine returned no profile for this person. */
  risk: RiskProfile | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

/**
 * Renders the rule engine's own output: the score, band, per-signal points and
 * the reasons it returned. Nothing is re-weighted or explained beyond that.
 */
export function PersonRiskPanel({
  risk,
  isLoading,
  error,
  onRetry,
}: PersonRiskPanelProps) {
  const signalSource = risk?.signals ?? risk?.signal_scores
  const signals = signalSource
    ? SIGNAL_KEYS.filter((key) => typeof signalSource[key] === 'number')
        .map((key) => ({
          key,
          label: RISK_SIGNAL_LABELS[key],
          points: signalSource[key] as number,
        }))
        .sort((a, b) => b.points - a.points || a.label.localeCompare(b.label))
    : []
  const reasons = risk?.risk_reasons ?? []

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Risk assessment"
        description="Explainable rule-engine output from /analytics/risk."
        icon={<ShieldAlert size={15} strokeWidth={1.75} />}
        actions={
          risk ? (
            <RiskBadge level={risk.risk_level} score={risk.risk_score} />
          ) : null
        }
      />

      {error && !risk ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : isLoading && !risk ? (
        <PanelBody className="space-y-3">
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-3 w-36" />
        </PanelBody>
      ) : !risk ? (
        <PanelBody>
          <p className="text-xs leading-relaxed text-ink-muted">
            No risk profile was returned for this person. The rule engine scores
            person entities only.
          </p>
        </PanelBody>
      ) : (
        <div className="flex flex-1 flex-col">
          <div className="border-b border-line px-4 py-3">
            <RiskScoreBar score={risk.risk_score} level={risk.risk_level} />
          </div>

          <div className="border-b border-line px-4 py-3">
            <p className="mb-2 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
              Risk signals
            </p>
            <ul className="space-y-1">
              {signals.map((signal) => (
                <li
                  key={signal.key}
                  className="flex items-baseline justify-between gap-3"
                >
                  <span
                    className={cn(
                      'text-xs',
                      signal.points > 0 ? 'text-ink' : 'text-ink-faint',
                    )}
                  >
                    {signal.label}
                  </span>
                  <span
                    className={cn(
                      'shrink-0 font-mono text-2xs tabular-nums',
                      signal.points > 0 ? 'text-ink-muted' : 'text-ink-faint',
                    )}
                  >
                    {signal.points}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {reasons.length > 0 ? (
            <div className="px-4 py-3">
              <p className="mb-2 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
                Contributing reasons
              </p>
              <ul className="space-y-1.5">
                {reasons.map((reason) => (
                  <li
                    key={reason}
                    className="flex gap-2 text-xs leading-snug text-ink-muted"
                  >
                    <span
                      aria-hidden
                      className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ink-faint"
                    />
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <p className="mt-auto border-t border-line px-4 py-2 text-2xs text-ink-faint">
            Scoring method:{' '}
            <span className="font-mono">{risk.scoring_method}</span>
          </p>
        </div>
      )}
    </Panel>
  )
}
