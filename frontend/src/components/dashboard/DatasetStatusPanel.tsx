import type { ReactNode } from 'react'

import {
  Panel,
  PanelBody,
  PanelHeader,
  Skeleton,
  StatusIndicator,
} from '@/components/ui'
import type { StatusTone } from '@/components/ui'
import type { ApiReachability, NetworkAvailability } from '@/hooks'
import { formatNumber } from '@/lib/format'
import { API_BASE_URL } from '@/services'

export interface DatasetStatusPanelProps {
  apiReachability: ApiReachability
  networkAvailability: NetworkAvailability
  /** `scoring_method` reported by /analytics/risk. */
  scoringMethod: string | null
  /** Null while loading, or when the source request failed. */
  peopleScored: number | null
  riskFailed: boolean
  communityCount: number | null
  communitiesFailed: boolean
  anomalyExtreme: number | null
  anomalyHigh: number | null
  anomaliesFailed: boolean
  lastRefreshedAt: Date | null
}

const API_TONE: Record<ApiReachability, StatusTone> = {
  checking: 'pending',
  online: 'online',
  degraded: 'degraded',
  offline: 'offline',
}

const API_LABEL: Record<ApiReachability, string> = {
  checking: 'Checking',
  online: 'Online',
  degraded: 'Partial',
  offline: 'Offline',
}

const NETWORK_TONE: Record<NetworkAvailability, StatusTone> = {
  loading: 'pending',
  loaded: 'online',
  unavailable: 'offline',
}

const NETWORK_LABEL: Record<NetworkAvailability, string> = {
  loading: 'Loading',
  loaded: 'Loaded',
  unavailable: 'Unavailable',
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="shrink-0 text-xs text-ink-muted">{label}</span>
      <span className="min-w-0 truncate text-right text-xs text-ink">
        {children}
      </span>
    </div>
  )
}

/** Loading skeleton, an unavailable marker on failure, or the value. */
function CountValue({ value, failed }: { value: number | null; failed: boolean }) {
  if (value !== null) {
    return (
      <span className="font-mono tabular-nums">{formatNumber(value)}</span>
    )
  }

  if (failed) return <span className="text-ink-faint">—</span>

  return <Skeleton className="ml-auto h-3 w-10" />
}

/**
 * Dataset context for the loaded graph. Statuses reflect the outcomes of this
 * page's own requests rather than a separate poll.
 */
export function DatasetStatusPanel({
  apiReachability,
  networkAvailability,
  scoringMethod,
  peopleScored,
  riskFailed,
  communityCount,
  communitiesFailed,
  anomalyExtreme,
  anomalyHigh,
  anomaliesFailed,
  lastRefreshedAt,
}: DatasetStatusPanelProps) {
  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Dataset status"
        description="Source and state of the data on this screen."
      />

      <PanelBody className="flex flex-1 flex-col divide-y divide-line py-1">
        <Row label="API">
          <StatusIndicator
            tone={API_TONE[apiReachability]}
            label={API_LABEL[apiReachability]}
          />
        </Row>

        <Row label="Network graph">
          <StatusIndicator
            tone={NETWORK_TONE[networkAvailability]}
            label={NETWORK_LABEL[networkAvailability]}
          />
        </Row>

        <Row label="Risk engine">
          {scoringMethod ? (
            <code className="font-mono text-2xs">{scoringMethod}</code>
          ) : (
            <span className="text-ink-faint">—</span>
          )}
        </Row>

        <Row label="People scored">
          <CountValue value={peopleScored} failed={riskFailed} />
        </Row>

        <Row label="Communities">
          <CountValue value={communityCount} failed={communitiesFailed} />
        </Row>

        <Row label="Anomaly extreme">
          <CountValue value={anomalyExtreme} failed={anomaliesFailed} />
        </Row>

        <Row label="Anomaly high">
          <CountValue value={anomalyHigh} failed={anomaliesFailed} />
        </Row>

        <Row label="Endpoint">
          <code className="font-mono text-2xs text-ink-muted">
            {API_BASE_URL}
          </code>
        </Row>

        <Row label="Last refreshed">
          {lastRefreshedAt ? (
            <span className="font-mono text-2xs tabular-nums">
              {lastRefreshedAt.toLocaleTimeString()}
            </span>
          ) : (
            <span className="text-ink-faint">—</span>
          )}
        </Row>
      </PanelBody>
    </Panel>
  )
}
