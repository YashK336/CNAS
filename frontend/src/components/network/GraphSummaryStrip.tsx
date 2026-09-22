import { Panel, PanelBody, SectionError, Skeleton } from '@/components/ui'
import { formatNumber } from '@/lib/format'
import type { NetworkSummary } from '@/types'

export interface GraphSummaryStripProps {
  summary: NetworkSummary | null
  error: string | null
  onRetry: () => void
  visibleNodes: number
  visibleLinks: number
  /** Aggregated link groups available across the whole graph. */
  totalDrawnLinks: number
  /** Full graph node count, so the overview subset is explicit. */
  totalNodes: number
}

/** Live graph size from `/network/summary`, plus what is currently on screen. */
export function GraphSummaryStrip({
  summary,
  error,
  onRetry,
  visibleNodes,
  visibleLinks,
  totalDrawnLinks,
  totalNodes,
}: GraphSummaryStripProps) {
  if (error && !summary) {
    return (
      <Panel>
        <SectionError message={error} onRetry={onRetry} compact />
      </Panel>
    )
  }

  return (
    <Panel>
      <PanelBody className="p-2.5">
        <div className="grid grid-cols-2 gap-2">
          {(
            [
              { label: 'Nodes', value: summary?.nodes },
              { label: 'Links', value: summary?.edges },
            ] as const
          ).map((metric) => (
            <div
              key={metric.label}
              className="rounded-sm border border-line bg-surface-raised px-2 py-1.5"
            >
              <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
                {metric.label}
              </p>
              {metric.value === undefined ? (
                <Skeleton className="mt-1 h-4 w-12" />
              ) : (
                <p className="mt-0.5 font-mono text-sm leading-none text-ink tabular-nums">
                  {formatNumber(metric.value)}
                </p>
              )}
            </div>
          ))}
        </div>

        <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
          Showing{' '}
          <span className="font-mono text-ink-muted tabular-nums">
            {formatNumber(visibleNodes)}
          </span>
          {totalNodes > 0 ? (
            <>
              {' '}
              of{' '}
              <span className="font-mono text-ink-muted tabular-nums">
                {formatNumber(totalNodes)}
              </span>
            </>
          ) : null}{' '}
          entities and{' '}
          <span className="font-mono text-ink-muted tabular-nums">
            {formatNumber(visibleLinks)}
          </span>{' '}
          of{' '}
          <span className="font-mono text-ink-muted tabular-nums">
            {formatNumber(totalDrawnLinks)}
          </span>{' '}
          aggregated links.
        </p>
      </PanelBody>
    </Panel>
  )
}
