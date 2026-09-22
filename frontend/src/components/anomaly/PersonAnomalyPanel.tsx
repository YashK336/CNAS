import { Activity } from 'lucide-react'

import { AnomalyBadge } from '@/components/anomaly/AnomalyBadge'
import {
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { ANOMALY_FEATURE_LABELS } from '@/lib/anomaly'
import type { AnomalyFeatureScores, AnomalyProfile } from '@/types'

const FEATURE_KEYS = Object.keys(
  ANOMALY_FEATURE_LABELS,
) as (keyof AnomalyFeatureScores)[]

export interface PersonAnomalyPanelProps {
  anomaly: AnomalyProfile | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

/**
 * Compact behavioral-anomaly readout. Scores describe unusual activity
 * relative to this dataset, not a finding of criminal behavior.
 */
export function PersonAnomalyPanel({
  anomaly,
  isLoading,
  error,
  onRetry,
}: PersonAnomalyPanelProps) {
  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Behavioral anomaly"
        description="Behavioral anomaly indicator — unusual activity vs the current dataset, not a finding of criminal behavior."
        icon={<Activity size={15} strokeWidth={1.75} />}
        actions={
          anomaly ? (
            <AnomalyBadge
              level={anomaly.anomaly_level}
              score={anomaly.anomaly_score}
            />
          ) : null
        }
      />

      {error && !anomaly ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : isLoading && !anomaly ? (
        <PanelBody className="space-y-2.5">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
        </PanelBody>
      ) : !anomaly ? (
        <PanelBody>
          <p className="text-xs leading-relaxed text-ink-muted">
            No behavioral anomaly profile was returned for this person.
          </p>
        </PanelBody>
      ) : (
        <div className="flex flex-1 flex-col">
          <ul className="grid grid-cols-2 gap-px border-b border-line bg-line sm:grid-cols-4">
            {FEATURE_KEYS.map((key) => (
              <li key={key} className="bg-surface px-4 py-2.5">
                <p className="text-2xs tracking-wide text-ink-faint uppercase">
                  {ANOMALY_FEATURE_LABELS[key]}
                </p>
                <p className="mt-1 font-mono text-sm text-ink tabular-nums">
                  {anomaly.feature_scores[key].toFixed(2)}
                </p>
              </li>
            ))}
          </ul>

          {anomaly.reasons.length > 0 ? (
            <div className="px-4 py-3">
              <p className="mb-2 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
                Indicators
              </p>
              <ul className="space-y-1.5">
                {anomaly.reasons.map((reason) => (
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
          ) : (
            <p className="px-4 py-3 text-xs text-ink-muted">
              Observed activity is within the typical range for this dataset.
            </p>
          )}

          <p className="mt-auto border-t border-line px-4 py-2 text-2xs text-ink-faint">
            Method: <span className="font-mono">{anomaly.method}</span>
          </p>
        </div>
      )}
    </Panel>
  )
}
