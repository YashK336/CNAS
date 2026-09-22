import { useCallback, useMemo } from 'react'

import {
  centralityResource,
  personsResource,
  riskProfilesResource,
} from '@/services'
import { buildRosterRows } from '@/lib/people'
import type {
  CentralityResult,
  Person,
  PersonRosterRow,
  RiskProfile,
} from '@/types'
import { useAsyncResource } from './useAsyncResource'
import type { AsyncResource } from './useAsyncResource'

export interface PeopleRoster {
  persons: AsyncResource<Person[]>
  centrality: AsyncResource<CentralityResult[]>
  risk: AsyncResource<RiskProfile[]>
  /** Joined rows; null until `/entities/persons` has resolved. */
  rows: PersonRosterRow[] | null
  /** Most recent moment any of the three requests settled. */
  lastLoadedAt: Date | null
  reload: () => void
}

/**
 * Loads the roster from the three list endpoints in parallel.
 *
 * Each request owns its own state, so a failing analysis endpoint leaves the
 * identity columns intact and only blanks the columns it feeds. All three are
 * session-cached: returning from a profile re-renders the table without
 * hitting the backend again, and `reload` is the only way to refetch.
 */
export function usePeopleRoster(): PeopleRoster {
  const persons = useAsyncResource<Person[]>((options) =>
    personsResource.load(options),
  )

  const centrality = useAsyncResource<CentralityResult[]>((options) =>
    centralityResource.load(options),
  )

  const risk = useAsyncResource<RiskProfile[]>((options) =>
    riskProfilesResource.load(options),
  )

  const rows = useMemo(
    () =>
      persons.data
        ? buildRosterRows(persons.data, centrality.data, risk.data)
        : null,
    [persons.data, centrality.data, risk.data],
  )

  const settledTimes = [persons, centrality, risk]
    .map((resource) => resource.settledAt?.getTime())
    .filter((time): time is number => time !== undefined)

  const lastLoadedAt =
    settledTimes.length > 0 ? new Date(Math.max(...settledTimes)) : null

  const refetchPersons = persons.refetch
  const refetchCentrality = centrality.refetch
  const refetchRisk = risk.refetch

  const reload = useCallback(() => {
    personsResource.invalidate()
    centralityResource.invalidate()
    riskProfilesResource.invalidate()

    refetchPersons()
    refetchCentrality()
    refetchRisk()
  }, [refetchPersons, refetchCentrality, refetchRisk])

  return { persons, centrality, risk, rows, lastLoadedAt, reload }
}
