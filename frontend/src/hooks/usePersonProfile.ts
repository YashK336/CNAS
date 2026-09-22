import { useCallback, useMemo } from 'react'

import {
  anomaliesResource,
  centralityResource,
  networkGraphResource,
  personAnomalyResource,
  personRecordResource,
  personRiskResource,
  personsResource,
  riskProfilesResource,
} from '@/services'
import { getGraphIndex } from '@/lib/graph'
import { buildPersonProfile } from '@/lib/people'
import type {
  CentralityResult,
  GraphIndex,
  NetworkGraph,
  PersonAnomalyLookup,
  PersonLookup,
  PersonProfile,
  PersonRiskLookup,
} from '@/types'
import { useAsyncResource } from './useAsyncResource'
import type { AsyncResource } from './useAsyncResource'

export interface PersonProfileData {
  person: AsyncResource<PersonLookup>
  risk: AsyncResource<PersonRiskLookup>
  anomaly: AsyncResource<PersonAnomalyLookup>
  centrality: AsyncResource<CentralityResult[]>
  graph: AsyncResource<NetworkGraph>
  index: GraphIndex | null
  /** Null until the person record resolves, or when the id does not exist. */
  profile: PersonProfile | null
  /** The backend confirmed this id is not in the dataset. */
  notFound: boolean
  reload: () => void
}

/**
 * Loads one person's intelligence profile.
 *
 * Identity and risk are read from the roster caches when the analyst arrived
 * from `/people`, and fall back to the per-person endpoints on a cold URL —
 * `/analytics/risk/{id}` recomputes every score on the backend, so the cached
 * list is worth preferring. The full graph is fetched only here, because it is
 * the only source of a person's relationships.
 */
export function usePersonProfile(personId: string): PersonProfileData {
  const person = useAsyncResource<PersonLookup>(
    (options) => {
      const cached = personsResource
        .peek()
        ?.find((entry) => String(entry.person_id) === personId)

      return cached
        ? Promise.resolve({ found: true, person: cached })
        : personRecordResource.for(personId).load(options)
    },
    [personId],
  )

  const risk = useAsyncResource<PersonRiskLookup>(
    (options) => {
      const cached = riskProfilesResource
        .peek()
        ?.find((entry) => String(entry.entity_id) === personId)

      return cached
        ? Promise.resolve({ found: true, risk: cached })
        : personRiskResource.for(personId).load(options)
    },
    [personId],
  )

  const anomaly = useAsyncResource<PersonAnomalyLookup>(
    (options) => {
      const cached = anomaliesResource
        .peek()
        ?.data.find((entry) => String(entry.entity_id) === personId)

      return cached
        ? Promise.resolve({ found: true, anomaly: cached })
        : personAnomalyResource.for(personId).load(options)
    },
    [personId],
  )

  const centrality = useAsyncResource<CentralityResult[]>((options) =>
    centralityResource.load(options),
  )

  const graph = useAsyncResource<NetworkGraph>((options) =>
    networkGraphResource.load(options),
  )

  const index = useMemo(
    () => (graph.data ? getGraphIndex(graph.data) : null),
    [graph.data],
  )

  const centralityEntry = useMemo(
    () =>
      centrality.data?.find(
        (entry) => String(entry.entity_id) === personId,
      ) ?? null,
    [centrality.data, personId],
  )

  const record = person.data?.found ? person.data.person : null

  const profile = useMemo(
    () =>
      record
        ? buildPersonProfile({
            personId,
            person: record,
            risk: risk.data?.found ? risk.data.risk : null,
            anomaly: anomaly.data?.found ? anomaly.data.anomaly : null,
            centrality: centralityEntry,
            index,
          })
        : null,
    [personId, record, risk.data, anomaly.data, centralityEntry, index],
  )

  const refetchPerson = person.refetch
  const refetchRisk = risk.refetch
  const refetchAnomaly = anomaly.refetch
  const refetchCentrality = centrality.refetch
  const refetchGraph = graph.refetch

  const reload = useCallback(() => {
    personsResource.invalidate()
    riskProfilesResource.invalidate()
    anomaliesResource.invalidate()
    centralityResource.invalidate()
    networkGraphResource.invalidate()
    personRecordResource.invalidate()
    personRiskResource.invalidate()
    personAnomalyResource.invalidate()

    refetchPerson()
    refetchRisk()
    refetchAnomaly()
    refetchCentrality()
    refetchGraph()
  }, [
    refetchPerson,
    refetchRisk,
    refetchAnomaly,
    refetchCentrality,
    refetchGraph,
  ])

  return {
    person,
    risk,
    anomaly,
    centrality,
    graph,
    index,
    profile,
    notFound: person.data?.found === false,
    reload,
  }
}
