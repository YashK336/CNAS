import type { KeyboardEvent, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { AnomalyBadge } from '@/components/anomaly/AnomalyBadge'
import {
  Panel,
  PanelHeader,
  SectionError,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
} from '@/components/ui'
import { EMPTY_VALUE, formatText } from '@/lib/format'
import type { AnomalyProfile } from '@/types'

const SKELETON_ROWS = 10
const VISIBLE_ROWS = 15

export interface AnomalySubjectsPanelProps {
  profiles: AnomalyProfile[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

export function AnomalySubjectsPanel({
  profiles,
  isLoading,
  error,
  onRetry,
}: AnomalySubjectsPanelProps) {
  const navigate = useNavigate()
  const rows = profiles?.slice(0, VISIBLE_ROWS) ?? null

  const openPerson = (personId: string) => {
    void navigate(`/people/${encodeURIComponent(personId)}`)
  }

  const onRowKeyDown = (
    event: KeyboardEvent<HTMLTableRowElement>,
    personId: string,
  ) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    openPerson(personId)
  }

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title="Highest anomaly subjects"
        description="Ranked by behavioral anomaly score. Unusual activity relative to this dataset — not a determination of criminal behavior."
      />

      {error && !rows ? (
        <SectionError message={error} onRetry={onRetry} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHeaderCell className="w-10">#</TableHeaderCell>
              <TableHeaderCell>Person</TableHeaderCell>
              <TableHeaderCell className="w-24">Person ID</TableHeaderCell>
              <TableHeaderCell className="w-32">Level</TableHeaderCell>
              <TableHeaderCell>Main reasons</TableHeaderCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows
              ? rows.map((profile, index) => {
                  const personId = String(profile.entity_id)
                  const name = formatText(profile.name)
                  const reason = profile.reasons[0] ?? EMPTY_VALUE

                  return (
                    <TableRow
                      key={personId}
                      interactive
                      tabIndex={0}
                      aria-label={`Open profile for ${name}`}
                      onClick={() => openPerson(personId)}
                      onKeyDown={(event) => onRowKeyDown(event, personId)}
                    >
                      <TableCell mono className="text-ink-faint">
                        {index + 1}
                      </TableCell>
                      <TableCell>
                        <Link
                          to={`/people/${encodeURIComponent(personId)}`}
                          onClick={(event: MouseEvent) =>
                            event.stopPropagation()
                          }
                          className="font-medium text-ink hover:text-accent"
                        >
                          {name}
                        </Link>
                      </TableCell>
                      <TableCell mono className="text-accent">
                        {personId}
                      </TableCell>
                      <TableCell>
                        <AnomalyBadge
                          level={profile.anomaly_level}
                          score={profile.anomaly_score}
                        />
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-ink-muted">
                        {reason}
                      </TableCell>
                    </TableRow>
                  )
                })
              : Array.from({ length: SKELETON_ROWS }, (_, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <Skeleton className="h-3 w-4" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-3 w-36" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-3 w-10" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-24" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-3 w-48" />
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      )}

      {isLoading ? (
        <span className="sr-only">Loading anomaly subjects</span>
      ) : null}
    </Panel>
  )
}
