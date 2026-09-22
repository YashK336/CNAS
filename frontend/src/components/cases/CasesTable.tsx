import { SearchX } from 'lucide-react'
import type { KeyboardEvent, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { RiskBadge } from '@/components/risk'
import {
  Button,
  EmptyState,
  LinkButton,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
} from '@/components/ui'
import { EMPTY_VALUE, formatDate, formatText } from '@/lib/format'
import type { CaseRow } from '@/types'

const SKELETON_ROWS = 12

export interface CasesTableProps {
  rows: CaseRow[] | null
  filtering: boolean
  onClearFilters: () => void
  riskUnavailable: boolean
}

export function CasesTable({
  rows,
  filtering,
  onClearFilters,
  riskUnavailable,
}: CasesTableProps) {
  const navigate = useNavigate()

  const openCase = (firId: string) => {
    void navigate(`/cases/${encodeURIComponent(firId)}`)
  }

  const onRowKeyDown = (
    event: KeyboardEvent<HTMLTableRowElement>,
    firId: string,
  ) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    openCase(firId)
  }

  if (rows !== null && rows.length === 0) {
    return filtering ? (
      <EmptyState
        icon={<SearchX size={16} strokeWidth={1.75} />}
        title="No FIRs match the current filters."
        description="Try a different FIR ID, crime, location or involved person."
        actions={
          <Button size="sm" onClick={onClearFilters}>
            Clear filters
          </Button>
        }
      />
    ) : (
      <EmptyState
        icon={<SearchX size={16} strokeWidth={1.75} />}
        title="No FIRs in the dataset."
        description="The backend returned an empty register from /cases."
      />
    )
  }

  return (
    <>
      <Table className="min-w-[56rem]">
        <TableHeader>
          <TableRow>
            <TableHeaderCell className="w-28">FIR ID</TableHeaderCell>
            <TableHeaderCell>Crime</TableHeaderCell>
            <TableHeaderCell className="w-32">Date</TableHeaderCell>
            <TableHeaderCell className="w-32">Location</TableHeaderCell>
            <TableHeaderCell>Person</TableHeaderCell>
            <TableHeaderCell className="w-32">Risk</TableHeaderCell>
            <TableHeaderCell className="w-24">Action</TableHeaderCell>
          </TableRow>
        </TableHeader>

        <TableBody>
          {rows
            ? rows.map((row) => {
                const firId = String(row.fir.fir_id)
                const personId =
                  row.involvedPerson?.entity_id ?? row.fir.person_id
                const personName = formatText(row.involvedPerson?.name)

                return (
                  <TableRow
                    key={firId}
                    interactive
                    tabIndex={0}
                    aria-label={`Open case ${firId}`}
                    onClick={() => openCase(firId)}
                    onKeyDown={(event) => onRowKeyDown(event, firId)}
                  >
                    <TableCell mono className="text-accent">
                      {firId}
                    </TableCell>

                    <TableCell>{formatText(row.fir.crime)}</TableCell>

                    <TableCell mono className="whitespace-nowrap text-ink-muted">
                      {formatDate(row.fir.date)}
                    </TableCell>

                    <TableCell className="text-ink-muted">
                      {formatText(row.fir.location)}
                    </TableCell>

                    <TableCell>
                      {personId ? (
                        <div className="min-w-0">
                          <Link
                            to={`/people/${encodeURIComponent(personId)}`}
                            onClick={(event: MouseEvent) =>
                              event.stopPropagation()
                            }
                            className="font-medium text-ink hover:text-accent"
                          >
                            {personName}
                          </Link>
                          <p className="font-mono text-2xs text-ink-faint">
                            {personId}
                          </p>
                        </div>
                      ) : (
                        <span className="text-ink-faint">{EMPTY_VALUE}</span>
                      )}
                    </TableCell>

                    <TableCell>
                      {row.riskLevel === null || row.riskScore === null ? (
                        <span className="text-ink-faint">{EMPTY_VALUE}</span>
                      ) : (
                        <RiskBadge
                          level={row.riskLevel}
                          score={row.riskScore}
                        />
                      )}
                    </TableCell>

                    <TableCell onClick={(event) => event.stopPropagation()}>
                      <LinkButton
                        to={`/cases/${encodeURIComponent(firId)}`}
                        size="sm"
                      >
                        Open
                      </LinkButton>
                    </TableCell>
                  </TableRow>
                )
              })
            : Array.from({ length: SKELETON_ROWS }, (_, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <Skeleton className="h-3 w-16" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-3 w-28" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-3 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-3 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-3 w-32" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-24" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-6 w-12" />
                  </TableCell>
                </TableRow>
              ))}
        </TableBody>
      </Table>

      {riskUnavailable ? (
        <p className="border-t border-line px-4 py-2 text-2xs text-signal-medium">
          Risk column unavailable — /analytics/risk did not respond.
        </p>
      ) : null}
    </>
  )
}
