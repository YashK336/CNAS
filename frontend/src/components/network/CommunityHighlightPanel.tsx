import {
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { sortCommunitiesBySize } from '@/lib/dashboard'
import { formatNumber } from '@/lib/format'
import type { Community } from '@/types'

export interface CommunityHighlightPanelProps {
  communities: Community[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
  selectedCommunityId: number | null
  onSelect: (community: Community | null) => void
}

/**
 * Highlights an existing community in place. The graph is never rebuilt around
 * a community, so positions stay stable while members are emphasised.
 */
export function CommunityHighlightPanel({
  communities,
  isLoading,
  error,
  onRetry,
  selectedCommunityId,
  onSelect,
}: CommunityHighlightPanelProps) {
  const ranked = communities ? sortCommunitiesBySize(communities) : null

  return (
    <Panel>
      <PanelHeader
        title="Communities"
        description="Select a cluster to highlight its members."
        actions={
          selectedCommunityId !== null ? (
            <button
              type="button"
              onClick={() => onSelect(null)}
              className="text-2xs text-ink-faint hover:text-ink"
            >
              Clear
            </button>
          ) : null
        }
      />

      {error && !ranked ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : (
        <PanelBody className="space-y-0.5 px-2.5 py-2.5">
          {!ranked
            ? Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-6 w-full" />
              ))
            : ranked.map((community) => {
                const active = community.community_id === selectedCommunityId

                return (
                  <button
                    key={community.community_id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => onSelect(community)}
                    className={cn(
                      'flex w-full items-center justify-between gap-2 rounded-sm border px-2 py-1 text-xs',
                      active
                        ? 'border-accent/50 bg-accent-muted text-accent'
                        : 'border-transparent text-ink hover:bg-surface-hover',
                    )}
                  >
                    <span className="truncate">
                      Community {community.community_id}
                    </span>
                    <span className="shrink-0 font-mono text-2xs tabular-nums">
                      {formatNumber(community.size)}
                    </span>
                  </button>
                )
              })}

          {isLoading ? (
            <span className="sr-only">Loading communities</span>
          ) : null}
        </PanelBody>
      )}
    </Panel>
  )
}
