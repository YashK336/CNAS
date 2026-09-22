import { ApiError, http } from './api'
import type { RequestOptions } from './api'
import type {
  EntityMapping,
  ListResponse,
  LocationRecord,
  Person,
  PersonLookup,
  Vehicle,
} from '@/types'

export function fetchPersons(
  options?: RequestOptions,
): Promise<ListResponse<Person>> {
  return http.get<ListResponse<Person>>('/entities/persons', options)
}

export function fetchPerson(
  personId: string,
  options?: RequestOptions,
): Promise<Person> {
  return http.get<Person>(
    `/entities/persons/${encodeURIComponent(personId)}`,
    options,
  )
}

/**
 * `fetchPerson` variant that turns the backend's 404 into a value, so callers
 * can tell "no such person" apart from "the request failed".
 */
export function lookupPerson(
  personId: string,
  options?: RequestOptions,
): Promise<PersonLookup> {
  return fetchPerson(personId, options).then(
    (person): PersonLookup => ({ found: true, person }),
    (error: unknown): PersonLookup => {
      if (error instanceof ApiError && error.status === 404) {
        return { found: false }
      }
      throw error
    },
  )
}

export function fetchVehicles(
  options?: RequestOptions,
): Promise<ListResponse<Vehicle>> {
  return http.get<ListResponse<Vehicle>>('/entities/vehicles', options)
}

export function fetchPhones(
  options?: RequestOptions,
): Promise<ListResponse<EntityMapping>> {
  return http.get<ListResponse<EntityMapping>>('/entities/phones', options)
}

export function fetchLocations(
  options?: RequestOptions,
): Promise<ListResponse<LocationRecord>> {
  return http.get<ListResponse<LocationRecord>>('/entities/locations', options)
}
