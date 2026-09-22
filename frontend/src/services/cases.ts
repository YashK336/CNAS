import { ApiError, http } from './api'
import type { RequestOptions } from './api'
import type {
  CaseDetailResponse,
  CaseFilters,
  CaseListResponse,
  CaseLookup,
} from '@/types'

function casesPath(filters?: CaseFilters): string {
  const params = new URLSearchParams()

  const crime = filters?.crime?.trim()
  const location = filters?.location?.trim()
  const personId = filters?.person_id?.trim()

  if (crime) params.set('crime', crime)
  if (location) params.set('location', location)
  if (personId) params.set('person_id', personId)

  const query = params.toString()
  return query ? `/cases?${query}` : '/cases'
}

export function getCases(
  filters?: CaseFilters,
  options?: RequestOptions,
): Promise<CaseListResponse> {
  return http.get<CaseListResponse>(casesPath(filters), options)
}

export function getCase(
  firId: string,
  options?: RequestOptions,
): Promise<CaseDetailResponse> {
  return http.get<CaseDetailResponse>(
    `/cases/${encodeURIComponent(firId)}`,
    options,
  )
}

/**
 * `getCase` variant that turns the backend's 404 into a value, so callers can
 * tell "no such FIR" apart from "the request failed".
 */
export function lookupCase(
  firId: string,
  options?: RequestOptions,
): Promise<CaseLookup> {
  return getCase(firId, options).then(
    (record): CaseLookup => ({ found: true, case: record }),
    (error: unknown): CaseLookup => {
      if (error instanceof ApiError && error.status === 404) {
        return { found: false }
      }
      throw error
    },
  )
}
