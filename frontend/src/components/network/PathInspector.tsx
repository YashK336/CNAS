import { ArrowDown, CircleSlash2, Focus, Route, X } from 'lucide-react'

import {
  Badge,
  Button,
  EmptyState,
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { entityPrimaryLabel } from '@/lib/graph'
import { formatNumber } from '@/lib/format'
import type { ActivePath, GraphIndex, PathRole, TraceState } from '@/types'

export interface PathInspectorProps {
  state: TraceState
  index: GraphIndex
  onClear: () => void
  onFocus: () => void
  onRetry: () => void
  onSelectNode: (entityId: string) => void
}

const ROLE_LABEL: Record<PathRole, string> = {
  source: 'Source',
  step: 'Step',
  target: 'Target',
}

function HopChain({
  path,
  index,
  onSelectNode,
}: {
  path: ActivePath
  index: GraphIndex
  onSelectNode: (entityId: string) => void
}) {
  return (
    <ol className="space-y-0">
      {path.nodeIds.map((entityId, position) => {
        const node = index.nodesById.get(entityId)
        const hop = path.hops[position]
        const role: PathRole =
          position === 0
            ? 'source'
            : position === path.nodeIds.length - 1
              ? 'target'
              : 'step'

        return (
          <li key={`${entityId}-${position}`}>
            <button
              type="button"
              onClick={() => onSelectNode(entityId)}
              className={cn(
                'flex w-full items-center gap-2 rounded-sm border px-2 py-1.5 text-left hover:bg-surface-hover',
                role === 'step'
                  ? 'border-line bg-surface-raised'
                  : 'border-accent/45 bg-accent-muted',
              )}
            >
              <span
                className={cn(
                  'w-[42px] shrink-0 text-[9px] font-semibold tracking-widest uppercase',
                  role === 'step' ? 'text-ink-faint' : 'text-accent',
                )}
              >
                {ROLE_LABEL[role]}
              </span>
              <span className="min-w-0 flex-1 truncate text-xs text-ink">
                {node ? entityPrimaryLabel(node) : entityId}
              </span>
              <span className="shrink-0 font-mono text-2xs text-ink-faint">
                {entityId}
              </span>
            </button>

            {hop ? (
              <div className="flex items-center gap-1.5 py-1 pl-3 text-2xs text-accent">
                <ArrowDown size={11} strokeWidth={2} aria-hidden />
                <span className="font-mono tracking-wide">
                  {hop.relationship ?? 'RELATED_TO'}
                </span>
              </div>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}

/**
 * Result of a connection trace. Rendered only once a trace has been attempted.
 */
export function PathInspector({
  state,
  index,
  onClear,
  onFocus,
  onRetry,
  onSelectNode,
}: PathInspectorProps) {
  if (state.status === 'idle') return null

  return (
    <Panel>
      <PanelHeader
        title="Traced path"
        icon={<Route size={13} strokeWidth={1.75} />}
        actions={
          state.status === 'found' ? (
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                className="px-1.5"
                onClick={onFocus}
                icon={<Focus size={12} strokeWidth={1.75} />}
                title="Zoom to path"
                aria-label="Zoom to path"
              />
              <Button
                size="sm"
                onClick={onClear}
                icon={<X size={12} strokeWidth={1.75} />}
              >
                Clear path
              </Button>
            </div>
          ) : (
            <Button size="sm" onClick={onClear}>
              Dismiss
            </Button>
          )
        }
      />

      {state.status === 'loading' ? (
        <PanelBody className="space-y-2 p-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-7 w-full" />
          <Skeleton className="h-7 w-full" />
          <Skeleton className="h-7 w-full" />
        </PanelBody>
      ) : null}

      {state.status === 'error' ? (
        <SectionError message={state.message} onRetry={onRetry} compact />
      ) : null}

      {state.status === 'not-found' ? (
        <PanelBody className="p-3">
          <EmptyState
            className="px-2 py-6"
            icon={<CircleSlash2 size={16} strokeWidth={1.75} />}
            title="No connection found between these entities."
            description={state.message}
          />
          <p className="border-t border-line pt-2.5 text-2xs leading-relaxed text-ink-faint">
            The backend searches directed links in the loaded datasets only. An
            absent path is not evidence that no association exists.
          </p>
        </PanelBody>
      ) : null}

      {state.status === 'found' ? (
        <PanelBody className="space-y-3 p-3">
          <div className="flex items-center justify-between gap-2">
            <Badge tone="accent">
              {formatNumber(state.path.degrees)}
              {state.path.degrees === 1
                ? ' degree of separation'
                : ' degrees of separation'}
            </Badge>
            <span className="font-mono text-2xs text-ink-faint">
              {formatNumber(state.path.hops.length)} hops
            </span>
          </div>

          <HopChain
            path={state.path}
            index={index}
            onSelectNode={onSelectNode}
          />
        </PanelBody>
      ) : null}
    </Panel>
  )
}
