import { Network, RefreshCw } from 'lucide-react'
import { Suspense, lazy, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

import {
  EmptyState,
  LinkButton,
  Panel,
  PanelHeader,
  SectionError,
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatNumber } from '@/lib/format'
import { ENTITY_PRESENTATION } from '@/lib/entities'
import { ENTITY_TYPES } from '@/types'
import type { PersonNeighbourhood } from '@/types'

/** React Flow is code-split; it must not weigh on the roster route. */
const LazyPersonNetworkCanvas = lazy(() =>
  import('./PersonNetworkCanvas').then((module) => ({
    default: module.PersonNetworkCanvas,
  })),
)

function CanvasLoading({ label }: { label: string }) {
  return (
    <EmptyState
      className="h-full"
      icon={<RefreshCw size={16} strokeWidth={1.75} className="animate-spin" />}
      title={label}
    />
  )
}

export interface PersonNetworkPanelProps {
  personId: string
  /** Null while `/network/graph` is loading or after it failed. */
  neighbourhood: PersonNeighbourhood | null
  error: string | null
  onRetry: () => void
}

/**
 * The person's immediate neighbourhood. Deliberately a star of direct links
 * only — the full graph, filters and path tracing live in Network Explorer,
 * which the header action opens focused on this person.
 */
export function PersonNetworkPanel({
  personId,
  neighbourhood,
  error,
  onRetry,
}: PersonNetworkPanelProps) {
  const navigate = useNavigate()

  const openEntity = useCallback(
    (entityId: string) => {
      if (entityId === personId) return

      // The entity type decides the destination, so ids are never pattern-matched.
      const node = neighbourhood?.view.nodes.find(
        (candidate) => candidate.id === entityId,
      )
      if (!node) return

      void navigate(
        node.entity.entity_type === 'person'
          ? `/people/${encodeURIComponent(entityId)}`
          : `/network?focus=${encodeURIComponent(entityId)}`,
      )
    },
    [navigate, neighbourhood, personId],
  )

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Network context"
        description="Entities linked directly to this person."
        icon={<Network size={15} strokeWidth={1.75} />}
        actions={
          <LinkButton
            to={`/network?focus=${encodeURIComponent(personId)}`}
            size="sm"
          >
            Open in Network Explorer
          </LinkButton>
        }
      />

      {error && !neighbourhood ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : (
        <>
          <div className="relative h-[420px]">
            {!neighbourhood ? (
              <CanvasLoading label="Loading network context…" />
            ) : neighbourhood.view.nodes.length === 0 ? (
              <EmptyState
                className="h-full"
                icon={<Network size={16} strokeWidth={1.75} />}
                title="Not present in the graph."
                description="The graph contains no node for this person, so there is no local neighbourhood to draw."
              />
            ) : neighbourhood.total === 0 ? (
              <EmptyState
                className="h-full"
                icon={<Network size={16} strokeWidth={1.75} />}
                title="No direct connections."
                description="This person has no edges in the current graph."
              />
            ) : (
              <div className="absolute inset-0">
                <Suspense
                  fallback={<CanvasLoading label="Preparing canvas…" />}
                >
                  <LazyPersonNetworkCanvas
                    view={neighbourhood.view}
                    onSelectEntity={openEntity}
                  />
                </Suspense>
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t border-line px-4 py-2 text-2xs text-ink-faint">
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
              {ENTITY_TYPES.map((type) => (
                <span key={type} className="flex items-center gap-1.5">
                  <span
                    aria-hidden
                    className={cn(
                      'h-1.5 w-1.5 rounded-full',
                      ENTITY_PRESENTATION[type].dotClass,
                    )}
                  />
                  {ENTITY_PRESENTATION[type].label}
                </span>
              ))}
            </span>

            {neighbourhood && neighbourhood.shown < neighbourhood.total ? (
              <span>
                Strongest {formatNumber(neighbourhood.shown)} of{' '}
                {formatNumber(neighbourhood.total)} direct connections
              </span>
            ) : null}
          </div>
        </>
      )}
    </Panel>
  )
}
