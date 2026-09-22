import { GitCompareArrows } from 'lucide-react'

import {
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { formatNumber } from '@/lib/format'
import type { RelationshipCount } from '@/types'

export interface ConnectionSummaryPanelProps {
  /** Null while `/network/graph` is loading or after it failed. */
  counts: RelationshipCount[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

/** One tile per relationship type, counting the underlying API edge records. */
export function ConnectionSummaryPanel({
  counts,
  isLoading,
  error,
  onRetry,
}: ConnectionSummaryPanelProps) {
  return (
    <Panel>
      <PanelHeader
        title="Connection summary"
        description="Edge records per relationship type, counted from the graph."
        icon={<GitCompareArrows size={15} strokeWidth={1.75} />}
      />

      {error && !counts ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : !counts ? (
        <PanelBody className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="space-y-1.5">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-4 w-10" />
            </div>
          ))}
          {isLoading ? (
            <span className="sr-only">Loading connection summary</span>
          ) : null}
        </PanelBody>
      ) : counts.length === 0 ? (
        <PanelBody>
          <p className="text-xs text-ink-muted">
            This person has no relationships in the current graph.
          </p>
        </PanelBody>
      ) : (
        <PanelBody className="grid grid-cols-2 gap-px bg-line p-0 sm:grid-cols-3 xl:grid-cols-4 [&>*]:bg-surface">
          {counts.map((entry) => (
            <div key={entry.relationship} className="px-3 py-2.5">
              <p
                className="truncate text-2xs tracking-wide text-ink-faint uppercase"
                title={entry.relationship}
              >
                {entry.relationship.replaceAll('_', ' ')}
              </p>
              <p className="mt-0.5 font-mono text-sm text-ink tabular-nums">
                {formatNumber(entry.interactions)}
              </p>
              <p className="text-2xs text-ink-faint">
                {formatNumber(entry.counterparts)}{' '}
                {entry.counterparts === 1 ? 'entity' : 'entities'}
              </p>
            </div>
          ))}
        </PanelBody>
      )}
    </Panel>
  )
}
