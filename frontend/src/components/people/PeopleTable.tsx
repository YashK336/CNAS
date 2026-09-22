import { ArrowDown, ArrowUp, ChevronsUpDown, SearchX } from 'lucide-react'
import type { KeyboardEvent, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { RiskBadge } from '@/components/risk'
import {
  Button,
  EmptyState,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { EMPTY_VALUE, formatText } from '@/lib/format'
import type {
  PeopleSort,
  PeopleSortKey,
  PersonRosterRow,
  SortDirection,
} from '@/types'

const SKELETON_ROWS = 12

/** Centrality values are small fractions; four decimals matches the backend. */
function formatMetric(value: number | null): string {
  return value === null ? EMPTY_VALUE : value.toFixed(4)
}

interface SortControlProps {
  label: string
  sortKey: PeopleSortKey
  /** Direction applied on the first click; numbers read best descending. */
  initialDirection: SortDirection
  sort: PeopleSort
  onSortChange: (sort: PeopleSort) => void
  className?: string
}

function SortControl({
  label,
  sortKey,
  initialDirection,
  sort,
  onSortChange,
  className,
}: SortControlProps) {
  const active = sort.key === sortKey
  const direction = active ? sort.direction : initialDirection

  return (
    <button
      type="button"
      onClick={() =>
        onSortChange({
          key: sortKey,
          direction: active
            ? direction === 'asc'
              ? 'desc'
              : 'asc'
            : initialDirection,
        })
      }
      aria-label={`Sort by ${label}`}
      title={`Sort by ${label}`}
      className={cn(
        'inline-flex items-center gap-1 rounded-sm whitespace-nowrap tracking-wider uppercase transition-colors',
        active ? 'text-accent' : 'text-ink-faint hover:text-ink',
        className,
      )}
    >
      {label}
      {active ? (
        direction === 'asc' ? (
          <ArrowUp size={11} strokeWidth={2.25} aria-hidden />
        ) : (
          <ArrowDown size={11} strokeWidth={2.25} aria-hidden />
        )
      ) : (
        <ChevronsUpDown size={11} strokeWidth={1.75} aria-hidden />
      )}
      <span className="sr-only">
        {active
          ? `, sorted ${direction === 'asc' ? 'ascending' : 'descending'}`
          : ', not sorted'}
      </span>
    </button>
  )
}

export interface PeopleTableProps {
  /** Already filtered and sorted; null while `/entities/persons` is in flight. */
  rows: PersonRosterRow[] | null
  sort: PeopleSort
  onSortChange: (sort: PeopleSort) => void
  /** Active search text, used to distinguish "no matches" from "no people". */
  query: string
  onClearSearch: () => void
  /** `/analytics/risk` did not respond, so the risk column cannot be filled. */
  riskUnavailable: boolean
  /** `/analytics/centrality` did not respond. */
  centralityUnavailable: boolean
}

/**
 * Dense roster. The whole row is the navigation target; the name is also a
 * real link so middle-click, keyboard focus and screen readers behave.
 */
export function PeopleTable({
  rows,
  sort,
  onSortChange,
  query,
  onClearSearch,
  riskUnavailable,
  centralityUnavailable,
}: PeopleTableProps) {
  const navigate = useNavigate()

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

  if (rows !== null && rows.length === 0) {
    return query.trim() === '' ? (
      <EmptyState
        icon={<SearchX size={16} strokeWidth={1.75} />}
        title="No people in the dataset."
        description="The backend returned an empty roster from /entities/persons."
      />
    ) : (
      <EmptyState
        icon={<SearchX size={16} strokeWidth={1.75} />}
        title="No people match your search."
        description={`Nothing matches “${query.trim()}” across name, person ID, phone, vehicle, bank account or city.`}
        actions={
          <Button size="sm" onClick={onClearSearch}>
            Clear search
          </Button>
        }
      />
    )
  }

  return (
    <>
      {/* Below this width the columns start wrapping mid-value; the wrapper
          scrolls horizontally instead, which keeps every row single-line. */}
      <Table className="min-w-[64rem]">
        <TableHeader>
          <TableRow>
            <TableHeaderCell className="w-10 text-right">#</TableHeaderCell>

            <TableHeaderCell className="min-w-44">
              <SortControl
                label="Person"
                sortKey="name"
                initialDirection="asc"
                sort={sort}
                onSortChange={onSortChange}
              />
            </TableHeaderCell>

            <TableHeaderCell className="w-28">
              <SortControl
                label="Person ID"
                sortKey="person_id"
                initialDirection="asc"
                sort={sort}
                onSortChange={onSortChange}
              />
            </TableHeaderCell>

            <TableHeaderCell className="w-36">Phone</TableHeaderCell>

            <TableHeaderCell className="w-28">
              <SortControl
                label="City"
                sortKey="city"
                initialDirection="asc"
                sort={sort}
                onSortChange={onSortChange}
              />
            </TableHeaderCell>

            <TableHeaderCell className="w-28">Vehicle</TableHeaderCell>

            <TableHeaderCell className="w-28">Bank account</TableHeaderCell>

            <TableHeaderCell className="w-32">
              <SortControl
                label="Risk"
                sortKey="risk"
                initialDirection="desc"
                sort={sort}
                onSortChange={onSortChange}
              />
            </TableHeaderCell>

            <TableHeaderCell className="w-44">
              <span className="block">Network rank</span>
              {/* Same two-column grid as the cells below, so each number sits
                  under the header it belongs to and no row needs its own label. */}
              <span className="mt-1 grid grid-cols-2 gap-2 text-[10px]">
                <SortControl
                  label="PageRank"
                  sortKey="pagerank"
                  initialDirection="desc"
                  sort={sort}
                  onSortChange={onSortChange}
                />
                <SortControl
                  label="Betweenness"
                  sortKey="betweenness"
                  initialDirection="desc"
                  sort={sort}
                  onSortChange={onSortChange}
                />
              </span>
            </TableHeaderCell>
          </TableRow>
        </TableHeader>

        <TableBody>
          {rows
            ? rows.map((row, index) => {
                const personId = String(row.person.person_id)
                const name = formatText(row.person.name)

                return (
                  <TableRow
                    key={personId}
                    interactive
                    tabIndex={0}
                    aria-label={`Open intelligence profile for ${name}`}
                    onClick={() => openPerson(personId)}
                    onKeyDown={(event) => onRowKeyDown(event, personId)}
                  >
                    <TableCell mono className="text-right text-ink-faint">
                      {index + 1}
                    </TableCell>

                    <TableCell>
                      <Link
                        to={`/people/${encodeURIComponent(personId)}`}
                        onClick={(event: MouseEvent) => event.stopPropagation()}
                        className="font-medium text-ink hover:text-accent"
                      >
                        {name}
                      </Link>
                    </TableCell>

                    <TableCell mono className="text-accent">
                      {personId}
                    </TableCell>

                    <TableCell mono className="whitespace-nowrap text-ink-muted">
                      {formatText(row.person.phone)}
                    </TableCell>

                    <TableCell className="text-ink-muted">
                      {formatText(row.person.home_city)}
                    </TableCell>

                    <TableCell mono className="text-ink-muted">
                      {formatText(row.person.vehicle_no)}
                    </TableCell>

                    <TableCell mono className="text-ink-muted">
                      {formatText(row.person.bank_account)}
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

                    <TableCell>
                      {row.pagerank === null && row.betweenness === null ? (
                        <span className="text-ink-faint">{EMPTY_VALUE}</span>
                      ) : (
                        <span className="grid grid-cols-2 gap-2 font-mono text-2xs tabular-nums">
                          <span className="text-ink">
                            {formatMetric(row.pagerank)}
                          </span>
                          <span className="text-ink-muted">
                            {formatMetric(row.betweenness)}
                          </span>
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })
            : Array.from({ length: SKELETON_ROWS }, (_, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <Skeleton className="ml-auto h-3 w-4" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-3 w-36" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-3 w-10" />
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
                    <Skeleton className="h-3 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-24" />
                  </TableCell>
                  <TableCell>
                    <span className="grid grid-cols-2 gap-2">
                      <Skeleton className="h-3 w-12" />
                      <Skeleton className="h-3 w-12" />
                    </span>
                  </TableCell>
                </TableRow>
              ))}
        </TableBody>
      </Table>

      {riskUnavailable || centralityUnavailable ? (
        <p className="border-t border-line px-4 py-2 text-2xs text-signal-medium">
          {riskUnavailable && centralityUnavailable
            ? 'Risk and network columns unavailable — /analytics/risk and /analytics/centrality did not respond.'
            : riskUnavailable
              ? 'Risk column unavailable — /analytics/risk did not respond.'
              : 'Network columns unavailable — /analytics/centrality did not respond.'}
        </p>
      ) : null}
    </>
  )
}
