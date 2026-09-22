import type { KeyboardEvent, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { RiskBadge } from '@/components/risk'
import {
  LinkButton,
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
import { joinInvestigativePriorities } from '@/lib/dashboard'
import { EMPTY_VALUE, formatText } from '@/lib/format'
import type { CentralityResult, RiskProfile } from '@/types'

export interface TopPrioritiesPanelProps {
  keyPersons: CentralityResult[] | null
  riskProfiles: RiskProfile[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
  /** True when /analytics/risk failed, so risk columns cannot be joined. */
  riskUnavailable: boolean
}

const SKELETON_ROWS = 10

export function TopPrioritiesPanel({
  keyPersons,
  riskProfiles,
  isLoading,
  error,
  onRetry,
  riskUnavailable,
}: TopPrioritiesPanelProps) {
  const navigate = useNavigate()

  const priorities = keyPersons
    ? joinInvestigativePriorities(keyPersons, riskProfiles)
    : null

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
        title="Top investigative priorities"
        description="Most influential people in the network, ranked by PageRank, with their current risk score."
        actions={
          <LinkButton to="/people" size="sm">
            All people
          </LinkButton>
        }
      />

      {error && !priorities ? (
        <SectionError message={error} onRetry={onRetry} />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHeaderCell className="w-10">#</TableHeaderCell>
                <TableHeaderCell>Person</TableHeaderCell>
                <TableHeaderCell className="w-32">Risk</TableHeaderCell>
                <TableHeaderCell className="w-24 text-right">
                  PageRank
                </TableHeaderCell>
                <TableHeaderCell className="w-28 text-right">
                  Betweenness
                </TableHeaderCell>
              </TableRow>
            </TableHeader>

            <TableBody>
              {priorities
                ? priorities.map((person, index) => (
                    <TableRow
                      key={person.entity_id}
                      interactive
                      tabIndex={0}
                      aria-label={`Open profile for ${formatText(person.name)}`}
                      onClick={() => openPerson(person.entity_id)}
                      onKeyDown={(event) =>
                        onRowKeyDown(event, person.entity_id)
                      }
                    >
                      <TableCell mono className="text-ink-faint">
                        {String(index + 1).padStart(2, '0')}
                      </TableCell>

                      <TableCell>
                        <Link
                          to={`/people/${encodeURIComponent(person.entity_id)}`}
                          onClick={(event: MouseEvent) =>
                            event.stopPropagation()
                          }
                          className="font-medium text-ink hover:text-accent"
                        >
                          {formatText(person.name)}
                        </Link>
                        <span className="ml-2 font-mono text-2xs text-ink-faint">
                          {person.entity_id}
                        </span>
                      </TableCell>

                      <TableCell>
                        {person.risk_level && person.risk_score !== null ? (
                          <RiskBadge
                            level={person.risk_level}
                            score={person.risk_score}
                          />
                        ) : (
                          <span className="text-ink-faint">{EMPTY_VALUE}</span>
                        )}
                      </TableCell>

                      <TableCell mono className="text-right">
                        {person.pagerank.toFixed(4)}
                      </TableCell>

                      <TableCell mono className="text-right">
                        {person.betweenness_centrality.toFixed(4)}
                      </TableCell>
                    </TableRow>
                  ))
                : Array.from({ length: SKELETON_ROWS }, (_, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Skeleton className="h-3 w-4" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-3 w-40" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-24" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="ml-auto h-3 w-12" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="ml-auto h-3 w-12" />
                      </TableCell>
                    </TableRow>
                  ))}
            </TableBody>
          </Table>

          {riskUnavailable ? (
            <p className="border-t border-line px-4 py-2 text-2xs text-signal-medium">
              Risk scores unavailable — /analytics/risk did not respond.
            </p>
          ) : null}

          {isLoading ? (
            <span className="sr-only">Loading investigative priorities</span>
          ) : null}
        </>
      )}
    </Panel>
  )
}
