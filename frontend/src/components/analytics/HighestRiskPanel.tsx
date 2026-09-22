import type { KeyboardEvent, MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { RiskBadge } from '@/components/risk'
import {
  EmptyState,
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
import type { RiskProfile } from '@/types'

const SKELETON_ROWS = ANALYTICS_RANK_LIMIT

export interface HighestRiskPanelProps {
  profiles: RiskProfile[] | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

export function HighestRiskPanel({
  profiles,
  isLoading,
  error,
  onRetry,
}: HighestRiskPanelProps) {
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
        title="Highest risk people"
        description="Ranked by risk score from GET /analytics/risk. Scores support prioritisation, not findings of guilt."
      />

      {error && !profiles ? (
        <SectionError message={error} onRetry={onRetry} />
      ) : profiles && profiles.length === 0 ? (
        <EmptyState
          title="No risk profiles"
          description="The backend returned an empty list from /analytics/risk."
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHeaderCell className="w-10">#</TableHeaderCell>
                <TableHeaderCell>Person</TableHeaderCell>
                <TableHeaderCell className="w-32">Risk</TableHeaderCell>
                <TableHeaderCell className="w-24 text-right">
                  Score
                </TableHeaderCell>
              </TableRow>
            </TableHeader>

            <TableBody>
              {profiles
                ? profiles.map((profile, index) => {
                    const personId = String(profile.entity_id)
                    const name = formatText(profile.name)

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

                        <TableCell>
                          <RiskBadge
                            level={profile.risk_level}
                            score={profile.risk_score}
                          />
                        </TableCell>

                        <TableCell mono className="text-right text-accent">
                          {profile.risk_score}
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
                        <Skeleton className="h-4 w-24" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="ml-auto h-3 w-8" />
                      </TableCell>
                    </TableRow>
                  ))}
            </TableBody>
          </Table>

          {isLoading ? (
            <span className="sr-only">Loading highest risk people</span>
          ) : null}
        </>
      )}
    </Panel>
  )
}
