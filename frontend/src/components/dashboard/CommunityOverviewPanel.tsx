import { Suspense } from 'react'
import { useNavigate } from 'react-router-dom'

import { LazyCommunitySizeChart } from '@/components/charts'
import {
  EmptyState,
  LinkButton,
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { sortCommunitiesBySize } from '@/lib/dashboard'
import { formatNumber } from '@/lib/format'
import type { Community } from '@/types'

export interface CommunityOverviewPanelProps {
  communities: Community[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

const MAX_BARS = 8
const ROW_HEIGHT = 34
const MIN_CHART_HEIGHT = 120

function ChartSkeleton({ rows }: { rows: number }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex items-center gap-3">
          <Skeleton className="h-3 w-20 shrink-0" />
          <Skeleton className="h-3 min-w-0 flex-1" />
        </div>
      ))}
    </div>
  )
}

export function CommunityOverviewPanel({
  communities,
  isLoading,
  error,
  onRetry,
}: CommunityOverviewPanelProps) {
  const navigate = useNavigate()

  const ranked = communities ? sortCommunitiesBySize(communities) : null

  const chartData =
    ranked?.slice(0, MAX_BARS).map((community) => ({
      label: `Community ${community.community_id}`,
      size: community.size,
    })) ?? []

  const chartHeight = Math.max(MIN_CHART_HEIGHT, chartData.length * ROW_HEIGHT)
  const largest = ranked?.[0]?.size ?? null

  const openNetworkExplorer = () => {
    void navigate('/network')
  }

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Community structure"
        description="Person clusters detected by modularity, largest first."
        actions={
          <LinkButton to="/network" size="sm">
            Network explorer
          </LinkButton>
        }
      />

      {error && !ranked ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : (
        <PanelBody className="flex flex-1 flex-col">
          {!ranked ? (
            <ChartSkeleton rows={3} />
          ) : chartData.length === 0 ? (
            <EmptyState
              title="No communities detected"
              description="The backend returned an empty community list for this network."
            />
          ) : (
            <Suspense fallback={<ChartSkeleton rows={chartData.length} />}>
              <LazyCommunitySizeChart
                data={chartData}
                height={chartHeight}
                onBarClick={openNetworkExplorer}
              />
            </Suspense>
          )}

          <div className="mt-auto flex items-center justify-between gap-3 border-t border-line pt-2.5 text-2xs text-ink-faint">
            {ranked ? (
              <>
                <span>
                  <span className="font-mono text-ink-muted tabular-nums">
                    {formatNumber(ranked.length)}
                  </span>{' '}
                  communities
                </span>
                {largest === null ? null : (
                  <span>
                    largest{' '}
                    <span className="font-mono text-ink-muted tabular-nums">
                      {formatNumber(largest)}
                    </span>{' '}
                    members
                  </span>
                )}
              </>
            ) : (
              <Skeleton className="h-3 w-32" />
            )}
          </div>

          {isLoading ? (
            <span className="sr-only">Loading community structure</span>
          ) : null}
        </PanelBody>
      )}
    </Panel>
  )
}
