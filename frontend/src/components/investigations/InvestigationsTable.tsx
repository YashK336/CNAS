import { Link } from 'react-router-dom'

import { ReportExportButtons } from '@/components/reports'
import { Badge, EmptyState, LinkButton, Skeleton } from '@/components/ui'
import { formatDateTime, formatNumber, formatText } from '@/lib/format'
import type { SavedInvestigation } from '@/types'

export interface InvestigationsTableProps {
  records: SavedInvestigation[] | null
  isLoading: boolean
}

export function InvestigationsTable({
  records,
  isLoading,
}: InvestigationsTableProps) {
  if (isLoading && !records) {
    return (
      <div className="space-y-2 p-3">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    )
  }

  if (!records || records.length === 0) {
    return (
      <EmptyState
        className="m-3"
        title="No saved investigations yet."
        description="Save a workspace from Network Explorer to resume an investigation later."
        actions={
          <LinkButton to="/network" variant="primary" size="sm">
            Open Network Explorer
          </LinkButton>
        }
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-xs">
        <thead className="border-b border-line bg-surface-raised text-2xs tracking-widest text-ink-faint uppercase">
          <tr>
            <th className="px-3 py-2 font-semibold">Investigation</th>
            <th className="px-3 py-2 font-semibold">Entities</th>
            <th className="px-3 py-2 font-semibold">Window</th>
            <th className="px-3 py-2 font-semibold">Jurisdiction</th>
            <th className="px-3 py-2 font-semibold">Updated</th>
            <th className="px-3 py-2 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr
              key={record.id}
              className="border-b border-line/70 hover:bg-surface-hover"
            >
              <td className="px-3 py-2.5 align-top">
                <div className="font-medium text-ink">{formatText(record.name)}</div>
                {record.description ? (
                  <p className="mt-0.5 max-w-md text-2xs text-ink-muted">
                    {record.description}
                  </p>
                ) : null}
                <p className="mt-1 font-mono text-2xs text-ink-faint">{record.id}</p>
              </td>
              <td className="px-3 py-2.5 align-top">
                <div className="flex flex-wrap gap-1">
                  {record.selected_entity_ids.slice(0, 4).map((entityId) => (
                    <Badge key={entityId} tone="neutral" mono>
                      {entityId}
                    </Badge>
                  ))}
                  {record.selected_entity_ids.length > 4 ? (
                    <Badge tone="neutral">
                      +{formatNumber(record.selected_entity_ids.length - 4)}
                    </Badge>
                  ) : null}
                </div>
                {record.graph_seeds.length > 0 ? (
                  <p className="mt-1 text-2xs text-ink-muted">
                    Seeds: {record.graph_seeds.join(', ')}
                  </p>
                ) : null}
              </td>
              <td className="px-3 py-2.5 align-top text-2xs text-ink-muted">
                {record.from_datetime || record.to_datetime ? (
                  <>
                    {formatDateTime(record.from_datetime)}
                    <br />→ {formatDateTime(record.to_datetime)}
                  </>
                ) : (
                  'All time'
                )}
              </td>
              <td className="px-3 py-2.5 align-top text-2xs text-ink-muted">
                {record.jurisdiction ? (
                  <Badge tone="neutral">{record.jurisdiction}</Badge>
                ) : (
                  'Legacy / admin only'
                )}
              </td>
              <td className="px-3 py-2.5 align-top text-2xs text-ink-muted">
                {formatDateTime(record.updated_at)}
              </td>
              <td className="px-3 py-2.5 align-top">
                <div className="flex flex-col items-start gap-2">
                  <Link
                    to={`/network?investigation=${encodeURIComponent(record.id)}`}
                    className="text-xs text-accent hover:underline"
                  >
                    Restore in Network
                  </Link>
                  <ReportExportButtons source="investigation" id={record.id} />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
