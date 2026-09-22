import { RefreshCw, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'

import { PeopleTable } from '@/components/people'
import {
  Button,
  EmptyState,
  Panel,
  SearchField,
  SectionHeader,
} from '@/components/ui'
import { usePeopleRoster } from '@/hooks'
import { formatNumber, formatTime } from '@/lib/format'
import { filterRosterRows, sortRosterRows } from '@/lib/people'
import type { PeopleSort } from '@/types'

/** Dataset order by default, so the first paint never reshuffles on load. */
const DEFAULT_SORT: PeopleSort = { key: 'person_id', direction: 'asc' }

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-2xs tracking-wide text-ink-faint uppercase">
        {label}
      </span>
      <span className="font-mono text-xs text-ink tabular-nums">{value}</span>
    </span>
  )
}

export function PeoplePage() {
  const { persons, centrality, risk, rows, lastLoadedAt, reload } =
    usePeopleRoster()

  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<PeopleSort>(DEFAULT_SORT)

  const visibleRows = useMemo(
    () => (rows ? sortRosterRows(filterRosterRows(rows, query), sort) : null),
    [rows, query, sort],
  )

  const rosterFailed = persons.error !== null && rows === null
  const isFiltering = query.trim() !== ''

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Entity intelligence"
        title="People"
        description="Searchable intelligence roster of persons in the dataset, with risk and network context."
        actions={
          <div className="flex items-center gap-4">
            <div className="hidden items-center gap-4 sm:flex">
              <Meta
                label="People"
                value={rows ? formatNumber(rows.length) : '—'}
              />
              {lastLoadedAt ? (
                <Meta label="Last loaded" value={formatTime(lastLoadedAt)} />
              ) : null}
            </div>

            <Button
              size="sm"
              onClick={reload}
              disabled={persons.isLoading}
              icon={
                <RefreshCw
                  size={13}
                  strokeWidth={1.75}
                  className={persons.isLoading ? 'animate-spin' : undefined}
                />
              }
            >
              {persons.isLoading ? 'Loading' : 'Reload'}
            </Button>
          </div>
        }
      />

      <Panel>
        {rosterFailed ? (
          <EmptyState
            icon={<TriangleAlert size={16} strokeWidth={1.75} />}
            title="Unable to load people."
            description={persons.error ?? undefined}
            actions={
              <Button
                onClick={reload}
                icon={<RefreshCw size={13} strokeWidth={1.75} />}
              >
                Retry
              </Button>
            }
          />
        ) : (
          <>
            <div className="border-b border-line p-3">
              <SearchField
                className="w-full max-w-md"
                label="Search people"
                placeholder="Name, person ID, phone, vehicle, bank account or city"
                value={query}
                onChange={setQuery}
                hint={
                  visibleRows && isFiltering
                    ? `${formatNumber(visibleRows.length)} / ${formatNumber(rows?.length ?? 0)}`
                    : undefined
                }
              />
            </div>

            <PeopleTable
              rows={visibleRows}
              sort={sort}
              onSortChange={setSort}
              query={query}
              onClearSearch={() => setQuery('')}
              riskUnavailable={risk.error !== null && risk.data === null}
              centralityUnavailable={
                centrality.error !== null && centrality.data === null
              }
            />
          </>
        )}
      </Panel>
    </div>
  )
}
