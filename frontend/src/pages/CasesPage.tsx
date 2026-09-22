import { RefreshCw, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'

import {
  CasesSummaryStrip,
  CasesTable,
} from '@/components/cases'
import {
  Button,
  EmptyState,
  Panel,
  SearchField,
  SectionHeader,
} from '@/components/ui'
import { useCasesExplorer } from '@/hooks'
import {
  EMPTY_CASE_FILTERS,
  filterCaseRows,
  hasActiveCaseFilters,
  uniqueSorted,
} from '@/lib/cases'
import { formatNumber, formatTime } from '@/lib/format'
import type { CaseExplorerFilters } from '@/types'

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

const selectClass =
  'h-8 min-w-36 rounded-sm border border-line-strong bg-surface-raised px-2 text-xs text-ink focus:border-accent/60 focus:outline-none'

export function CasesPage() {
  const { cases, risk, rows, summary, lastLoadedAt, reload } =
    useCasesExplorer()

  const [filters, setFilters] = useState<CaseExplorerFilters>(EMPTY_CASE_FILTERS)

  const crimeOptions = useMemo(
    () => uniqueSorted((cases.data ?? []).map((record) => record.crime)),
    [cases.data],
  )

  const locationOptions = useMemo(
    () => uniqueSorted((cases.data ?? []).map((record) => record.location)),
    [cases.data],
  )

  const visibleRows = useMemo(
    () => (rows ? filterCaseRows(rows, filters) : null),
    [rows, filters],
  )

  const filtering = hasActiveCaseFilters(filters)
  const rosterFailed = cases.error !== null && rows === null

  const update = (patch: Partial<CaseExplorerFilters>) => {
    setFilters((current) => ({ ...current, ...patch }))
  }

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Case intelligence"
        title="Cases / FIRs"
        description="Investigate reported crimes and their network connections."
        actions={
          <div className="flex items-center gap-4">
            <div className="hidden items-center gap-4 sm:flex">
              <Meta
                label="FIRs"
                value={summary ? formatNumber(summary.total) : '—'}
              />
              {lastLoadedAt ? (
                <Meta label="Last loaded" value={formatTime(lastLoadedAt)} />
              ) : null}
            </div>

            <Button
              size="sm"
              onClick={reload}
              disabled={cases.isLoading}
              icon={
                <RefreshCw
                  size={13}
                  strokeWidth={1.75}
                  className={cases.isLoading ? 'animate-spin' : undefined}
                />
              }
            >
              {cases.isLoading ? 'Loading' : 'Reload'}
            </Button>
          </div>
        }
      />

      <CasesSummaryStrip summary={summary} isLoading={cases.isLoading} />

      <Panel>
        {rosterFailed ? (
          <EmptyState
            icon={<TriangleAlert size={16} strokeWidth={1.75} />}
            title="Unable to load cases."
            description={cases.error ?? undefined}
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
            <div className="flex flex-wrap items-end gap-3 border-b border-line p-3">
              <SearchField
                className="min-w-56 flex-1"
                label="Search FIRs"
                placeholder="Search FIR ID, crime or person name"
                value={filters.query}
                onChange={(query) => update({ query })}
                hint={
                  visibleRows && filtering
                    ? `${formatNumber(visibleRows.length)} / ${formatNumber(rows?.length ?? 0)}`
                    : undefined
                }
              />

              <label className="flex min-w-36 flex-col gap-1">
                <span className="text-2xs tracking-wide text-ink-faint uppercase">
                  Crime
                </span>
                <select
                  className={selectClass}
                  value={filters.crime}
                  onChange={(event) => update({ crime: event.target.value })}
                  disabled={!cases.data}
                >
                  <option value="">All crimes</option>
                  {crimeOptions.map((crime) => (
                    <option key={crime} value={crime}>
                      {crime}
                    </option>
                  ))}
                </select>
              </label>

              <label className="flex min-w-36 flex-col gap-1">
                <span className="text-2xs tracking-wide text-ink-faint uppercase">
                  Location
                </span>
                <select
                  className={selectClass}
                  value={filters.location}
                  onChange={(event) => update({ location: event.target.value })}
                  disabled={!cases.data}
                >
                  <option value="">All locations</option>
                  {locationOptions.map((location) => (
                    <option key={location} value={location}>
                      {location}
                    </option>
                  ))}
                </select>
              </label>

              <Button
                size="sm"
                onClick={() => setFilters(EMPTY_CASE_FILTERS)}
                disabled={!filtering}
              >
                Clear filters
              </Button>
            </div>

            <CasesTable
              rows={visibleRows}
              filtering={filtering}
              onClearFilters={() => setFilters(EMPTY_CASE_FILTERS)}
              riskUnavailable={risk.error !== null && risk.data === null}
            />
          </>
        )}
      </Panel>
    </div>
  )
}
