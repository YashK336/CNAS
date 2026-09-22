import { History } from 'lucide-react'

import {
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatDuration,
  formatNumber,
} from '@/lib/format'
import type { PersonActivityEvent } from '@/types'

const VISIBLE_EVENTS = 25

/** Date-only backend values must not be rendered as midnight timestamps. */
function formatStamp(value: string): string {
  return /\d{1,2}:\d{2}/.test(value) ? formatDateTime(value) : formatDate(value)
}

function eventDetail(event: PersonActivityEvent): string | null {
  const parts: string[] = []

  if (event.amount !== null) parts.push(formatCurrency(event.amount))
  if (event.durationSeconds !== null) {
    parts.push(formatDuration(event.durationSeconds))
  }
  if (event.callType !== null) parts.push(event.callType)

  return parts.length > 0 ? parts.join(' · ') : null
}

export interface PersonActivityPanelProps {
  /** Null while `/network/graph` is loading or after it failed. */
  activity: PersonActivityEvent[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

/**
 * Dated relationship records, newest first. Only records that actually carry a
 * date appear — `OWNS` links have none anywhere in the dataset, so they are
 * absent rather than dated by guesswork.
 */
export function PersonActivityPanel({
  activity,
  isLoading,
  error,
  onRetry,
}: PersonActivityPanelProps) {
  const visible = activity?.slice(0, VISIBLE_EVENTS) ?? []
  const derivedFromEvent = visible.some((event) => event.fromEventNode)

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Recent activity"
        description="Timestamped graph relationships, newest first."
        icon={<History size={15} strokeWidth={1.75} />}
      />

      {error && !activity ? (
        <SectionError message={error} onRetry={onRetry} compact />
      ) : !activity ? (
        <PanelBody className="space-y-2.5">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="flex items-center justify-between gap-3">
              <Skeleton className="h-3 w-40" />
              <Skeleton className="h-3 w-20" />
            </div>
          ))}
          {isLoading ? (
            <span className="sr-only">Loading recent activity</span>
          ) : null}
        </PanelBody>
      ) : activity.length === 0 ? (
        <PanelBody>
          <p className="text-xs leading-relaxed text-ink-muted">
            No dated relationship record involves this person.
          </p>
        </PanelBody>
      ) : (
        <>
          <ul className="max-h-96 flex-1 divide-y divide-line overflow-y-auto">
            {visible.map((event) => {
              const detail = eventDetail(event)

              return (
                <li key={event.id} className="flex gap-3 px-4 py-2">
                  <div className="min-w-0 flex-1">
                    <p className="flex items-baseline gap-1.5">
                      <span className="shrink-0 text-2xs tracking-wide text-ink-faint uppercase">
                        {event.relationship.replaceAll('_', ' ')}
                      </span>
                      <span
                        aria-hidden
                        className="shrink-0 font-mono text-2xs text-ink-faint"
                      >
                        {event.outgoing ? '→' : '←'}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-xs text-ink">
                        {event.counterpartLabel}
                      </span>
                    </p>
                    {detail ? (
                      <p className="mt-0.5 text-2xs text-ink-muted">{detail}</p>
                    ) : null}
                  </div>

                  <span className="shrink-0 text-right font-mono text-2xs text-ink-muted">
                    {formatStamp(event.at)}
                    {event.fromEventNode ? (
                      <span aria-hidden className="text-ink-faint">
                        {' '}
                        †
                      </span>
                    ) : null}
                  </span>
                </li>
              )
            })}
          </ul>

          {activity.length > VISIBLE_EVENTS || derivedFromEvent ? (
            <div className="space-y-1 border-t border-line px-4 py-2 text-2xs text-ink-faint">
              {activity.length > VISIBLE_EVENTS ? (
                <p>
                  Showing the {formatNumber(VISIBLE_EVENTS)} most recent of{' '}
                  {formatNumber(activity.length)} dated records.
                </p>
              ) : null}
              {derivedFromEvent ? (
                <p>
                  † date read from the linked FIR or surveillance record, which
                  is where the backend stores it.
                </p>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </Panel>
  )
}
