import { ApiError } from './api'
import type { RequestOptions } from './api'
import { fetchCentrality, fetchAnomalies, getRiskScores, lookupPersonAnomaly, lookupPersonRisk } from './analytics'
import { getCases, lookupCase } from './cases'
import { fetchPersons, lookupPerson } from './entities'
import { fetchNetworkGraph } from './network'
import type {
  AnomalyResponse,
  CaseLookup,
  CaseRecord,
  CentralityResult,
  NetworkGraph,
  Person,
  PersonAnomalyLookup,
  PersonLookup,
  PersonRiskLookup,
  RiskProfile,
} from '@/types'

/** Read-through cache around a single expensive, session-stable GET. */
export interface SessionResource<T> {
  /** Resolves from cache, joins an in-flight request, or starts a new one. */
  load: (options?: RequestOptions) => Promise<T>
  /** The cached value, or null if it has never resolved. */
  peek: () => T | null
  /** Drops the cached value so the next `load` refetches. */
  invalidate: () => void
}

function abortRejection(signal: AbortSignal): Promise<never> {
  const reason = () => new ApiError('Request cancelled', { aborted: true })

  return new Promise((_, reject) => {
    if (signal.aborted) {
      reject(reason())
      return
    }
    signal.addEventListener('abort', () => reject(reason()), { once: true })
  })
}

/**
 * The backend rebuilds the whole NetworkX graph on every graph-derived
 * request, so the roster and the graph payload must not be refetched each time
 * a People route mounts. Values are held for the lifetime of the tab and
 * dropped explicitly by the reload actions.
 *
 * A cancelling consumer only stops awaiting the shared request — the request
 * itself keeps running, so concurrent consumers and the cache still settle.
 */
export function createSessionResource<T>(
  request: () => Promise<T>,
): SessionResource<T> {
  let value: T | null = null
  let inFlight: Promise<T> | null = null

  const start = (): Promise<T> => {
    if (value !== null) return Promise.resolve(value)
    if (inFlight) return inFlight

    const pending = request().then(
      (result) => {
        value = result
        inFlight = null
        return result
      },
      (error: unknown) => {
        inFlight = null
        throw error
      },
    )

    inFlight = pending
    return pending
  }

  return {
    load: (options) => {
      const pending = start()
      const signal = options?.signal
      return signal
        ? Promise.race([pending, abortRejection(signal)])
        : pending
    },
    peek: () => value,
    invalidate: () => {
      value = null
      inFlight = null
    },
  }
}

/** A `SessionResource` per key, for the per-entity endpoints. */
export interface KeyedSessionResource<T> {
  for: (key: string) => SessionResource<T>
  invalidate: () => void
}

export function createKeyedSessionResource<T>(
  request: (key: string) => Promise<T>,
): KeyedSessionResource<T> {
  const entries = new Map<string, SessionResource<T>>()

  return {
    for: (key) => {
      const existing = entries.get(key)
      if (existing) return existing

      const resource = createSessionResource(() => request(key))
      entries.set(key, resource)
      return resource
    },
    invalidate: () => entries.clear(),
  }
}

/* Shared session caches. Deliberately omit the caller's signal: the request is
   shared, so one consumer unmounting must not cancel it for the others. */

export const personsResource = createSessionResource<Person[]>(() =>
  fetchPersons().then((response) => response.data),
)

export const centralityResource = createSessionResource<CentralityResult[]>(
  () => fetchCentrality().then((response) => response.data),
)

export const riskProfilesResource = createSessionResource<RiskProfile[]>(() =>
  getRiskScores(),
)

export const networkGraphResource = createSessionResource<NetworkGraph>(() =>
  fetchNetworkGraph(),
)

export const personRecordResource = createKeyedSessionResource<PersonLookup>(
  (personId) => lookupPerson(personId),
)

/**
 * `/analytics/risk/{id}` rescores the entire dataset per call, so revisiting a
 * profile must reuse the answer. A 404 is cached too: it is just as stable.
 */
export const personRiskResource =
  createKeyedSessionResource<PersonRiskLookup>((personId) =>
    lookupPersonRisk(personId),
  )

export const anomaliesResource = createSessionResource<AnomalyResponse>(() =>
  fetchAnomalies(),
)

export const personAnomalyResource =
  createKeyedSessionResource<PersonAnomalyLookup>((personId) =>
    lookupPersonAnomaly(personId),
  )

export const casesResource = createSessionResource<CaseRecord[]>(() =>
  getCases().then((response) => response.data),
)

export const caseRecordResource = createKeyedSessionResource<CaseLookup>(
  (firId) => lookupCase(firId),
)

let importedDatasetGeneration = 0
const importedDatasetListeners = new Set<() => void>()

/** Subscribe to import-driven cache invalidation for always-mounted hooks. */
export function subscribeImportedDatasets(onStoreChange: () => void): () => void {
  importedDatasetListeners.add(onStoreChange)
  return () => {
    importedDatasetListeners.delete(onStoreChange)
  }
}

export function getImportedDatasetGeneration(): number {
  return importedDatasetGeneration
}

/** Drop roster/case/graph caches after a successful import so dependents refetch. */
export function invalidateImportedDatasets(): void {
  personsResource.invalidate()
  personRecordResource.invalidate()
  casesResource.invalidate()
  caseRecordResource.invalidate()
  centralityResource.invalidate()
  riskProfilesResource.invalidate()
  networkGraphResource.invalidate()
  anomaliesResource.invalidate()
  personRiskResource.invalidate()
  personAnomalyResource.invalidate()
  importedDatasetGeneration += 1
  importedDatasetListeners.forEach((listener) => listener())
}
