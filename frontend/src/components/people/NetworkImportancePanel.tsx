import { Share2 } from 'lucide-react'
import type { ReactNode } from 'react'

import { Panel, PanelBody, PanelHeader, Skeleton } from '@/components/ui'
import { EMPTY_VALUE, formatNumber } from '@/lib/format'
import type { CentralityResult } from '@/types'

export type MetricStatus = 'loading' | 'ready' | 'error'

interface MetricProps {
  label: string
  /** One-line plain-language meaning, so the number is interpretable. */
  hint: string
  status: MetricStatus
  value: ReactNode
}

function Metric({ label, hint, status, value }: MetricProps) {
  return (
    <div className="px-4 py-2.5">
      <p className="text-2xs tracking-wide text-ink-faint uppercase">{label}</p>
      <p className="mt-1 font-mono text-sm text-ink tabular-nums">
        {status === 'loading' ? (
          <Skeleton className="h-4 w-16" />
        ) : status === 'error' ? (
          <span className="text-ink-faint">{EMPTY_VALUE}</span>
        ) : (
          value
        )}
      </p>
      <p className="mt-1 text-2xs leading-snug text-ink-faint">{hint}</p>
    </div>
  )
}

export interface NetworkImportancePanelProps {
  /** Null when `/analytics/centrality` has no entry for this person. */
  centrality: CentralityResult | null
  centralityStatus: MetricStatus
  /** Distinct adjacent entities in `/network/graph`. */
  directConnections: number | null
  graphStatus: MetricStatus
}

/** Centrality straight from the backend; nothing is rescaled or re-ranked. */
export function NetworkImportancePanel({
  centrality,
  centralityStatus,
  directConnections,
  graphStatus,
}: NetworkImportancePanelProps) {
  const metricValue = (value: number | undefined) =>
    value === undefined ? (
      <span className="text-ink-faint">{EMPTY_VALUE}</span>
    ) : (
      value.toFixed(4)
    )

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Network importance"
        description="Centrality from /analytics/centrality, connections from /network/graph."
        icon={<Share2 size={15} strokeWidth={1.75} />}
      />

      {/* Not `flex-1`: stretching the rows would leave large gaps inside each
          tile when a neighbouring panel is taller. */}
      <PanelBody className="grid grid-cols-2 gap-px bg-line p-0 [&>*]:bg-surface">
        <Metric
          label="PageRank"
          hint="Influence carried by who links to them."
          status={centralityStatus}
          value={metricValue(centrality?.pagerank)}
        />
        <Metric
          label="Betweenness"
          hint="How often they sit between other entities."
          status={centralityStatus}
          value={metricValue(centrality?.betweenness_centrality)}
        />
        <Metric
          label="Degree centrality"
          /* The backend runs `nx.degree_centrality` over a multigraph, so
             parallel links are counted and the value can exceed 1. */
          hint="Link volume relative to network size; repeat links count."
          status={centralityStatus}
          value={metricValue(centrality?.degree_centrality)}
        />
        <Metric
          label="Direct connections"
          hint="Distinct entities linked in the graph."
          status={graphStatus}
          value={
            directConnections === null ? (
              <span className="text-ink-faint">{EMPTY_VALUE}</span>
            ) : (
              formatNumber(directConnections)
            )
          }
        />
      </PanelBody>
    </Panel>
  )
}
