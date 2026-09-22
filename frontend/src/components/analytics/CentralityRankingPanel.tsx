import type { KeyboardEvent, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import {
  EmptyState,
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
import { ANALYTICS_RANK_LIMIT } from '@/lib/analytics'
import { formatText } from '@/lib/format'
import type { CentralityResult } from '@/types'

const SKELETON_ROWS = ANALYTICS_RANK_LIMIT

export type CentralityRankKey = 'pagerank' | 'betweenness_centrality'

export interface CentralityRankingPanelProps {
  title: string
  description: string
  rankKey: CentralityRankKey
  results: CentralityResult[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

function formatMetric(value: number): string {
  return value.toFixed(4)
}

export function CentralityRankingPanel({
  title,
  description,
  rankKey,
  results,
  isLoading,
  error,
  onRetry,
}: CentralityRankingPanelProps) {
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

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title={title}
        description={description}
        actions={
          <LinkButton to="/people" size="sm">
            All people
          </LinkButton>
        }
      />

      {error && !results ? (
        <SectionError message={error} onRetry={onRetry} />
      ) : results && results.length === 0 ? (
        <EmptyState
          title="No centrality results"
          description="The backend returned an empty list from /analytics/centrality."
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHeaderCell className="w-10">#</TableHeaderCell>
                <TableHeaderCell>Person</TableHeaderCell>
                <TableHeaderCell className="w-24 text-right">
                  Degree
                </TableHeaderCell>
                <TableHeaderCell className="w-24 text-right">
                  PageRank
                </TableHeaderCell>
                <TableHeaderCell className="w-28 text-right">
                  Betweenness
                </TableHeaderCell>
              </TableRow>
            </TableHeader>

            <TableBody>
              {results
                ? results.map((person, index) => {
                    const personId = String(person.entity_id)
                    const name = formatText(person.name)

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
                          {String(index + 1).padStart(2, '0')}
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
                          <span className="ml-2 font-mono text-2xs text-ink-faint">
                            {personId}
                          </span>
                        </TableCell>

                        <TableCell mono className="text-right">
                          {formatMetric(person.degree_centrality)}
                        </TableCell>

                        <TableCell
                          mono
                          className={
                            rankKey === 'pagerank'
                              ? 'text-right text-accent'
                              : 'text-right'
                          }
                        >
                          {formatMetric(person.pagerank)}
                        </TableCell>

                        <TableCell
                          mono
                          className={
                            rankKey === 'betweenness_centrality'
                              ? 'text-right text-accent'
                              : 'text-right'
                          }
                        >
                          {formatMetric(person.betweenness_centrality)}
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
                        <Skeleton className="h-3 w-40" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="ml-auto h-3 w-12" />
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

          {isLoading ? (
            <span className="sr-only">Loading centrality rankings</span>
          ) : null}
        </>
      )}
    </Panel>
  )
}
