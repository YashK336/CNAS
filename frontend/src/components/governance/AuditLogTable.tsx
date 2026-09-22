import { Badge, EmptyState, Skeleton } from '@/components/ui'
import type { BadgeTone } from '@/components/ui/Badge'
import { formatDateTime, formatText } from '@/lib/format'
import type { AuditLogEvent } from '@/types'

export interface AuditLogTableProps {
  events: AuditLogEvent[] | null
  isLoading: boolean
}

function resultTone(result: AuditLogEvent['result']): BadgeTone {
  if (result === 'success') return 'low'
  if (result === 'denied') return 'medium'
  return 'critical'
}

export function AuditLogTable({ events, isLoading }: AuditLogTableProps) {
  if (isLoading && !events) {
    return (
      <div className="space-y-2 p-3">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    )
  }

  if (!events || events.length === 0) {
    return (
      <EmptyState
        className="m-3"
        title="No audit events recorded."
        description="Security-sensitive actions will appear here as append-only audit entries."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-xs">
        <thead className="border-b border-line bg-surface-raised text-2xs tracking-widest text-ink-faint uppercase">
          <tr>
            <th className="px-3 py-2 font-semibold">Timestamp</th>
            <th className="px-3 py-2 font-semibold">Actor</th>
            <th className="px-3 py-2 font-semibold">Action</th>
            <th className="px-3 py-2 font-semibold">Resource</th>
            <th className="px-3 py-2 font-semibold">Jurisdiction</th>
            <th className="px-3 py-2 font-semibold">Result</th>
            <th className="px-3 py-2 font-semibold">Metadata</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id} className="border-b border-line/70 hover:bg-surface-hover">
              <td className="px-3 py-2.5 align-top text-ink-muted">
                {formatDateTime(event.timestamp)}
              </td>
              <td className="px-3 py-2.5 align-top">
                {event.actor_username ? (
                  <div>
                    <div className="font-medium text-ink">{event.actor_username}</div>
                    {event.actor_id ? (
                      <p className="font-mono text-2xs text-ink-faint">{event.actor_id}</p>
                    ) : null}
                  </div>
                ) : (
                  '—'
                )}
              </td>
              <td className="px-3 py-2.5 align-top font-mono text-2xs text-ink-muted">
                {event.action}
              </td>
              <td className="px-3 py-2.5 align-top">
                <div className="font-mono text-2xs text-ink-muted">{event.resource_type}</div>
                {event.resource_id ? (
                  <p className="mt-0.5 font-mono text-2xs text-ink-faint">{event.resource_id}</p>
                ) : null}
              </td>
              <td className="px-3 py-2.5 align-top">
                {event.jurisdiction ? (
                  <Badge tone="accent">{event.jurisdiction}</Badge>
                ) : (
                  '—'
                )}
              </td>
              <td className="px-3 py-2.5 align-top">
                <Badge tone={resultTone(event.result)}>{event.result}</Badge>
              </td>
              <td className="px-3 py-2.5 align-top">
                {Object.keys(event.metadata).length > 0 ? (
                  <pre className="max-w-xs overflow-x-auto whitespace-pre-wrap font-mono text-2xs text-ink-muted">
                    {formatText(JSON.stringify(event.metadata))}
                  </pre>
                ) : (
                  '—'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
