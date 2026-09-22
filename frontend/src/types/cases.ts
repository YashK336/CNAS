/**
 * FIR / case shapes returned by `/cases` and `/cases/{fir_id}`.
 * Field names mirror fir.csv and the involved-person join from persons.csv.
 */

import type { RiskLevel } from './analytics'

/** Person linked through `person_id`. Fields exist on persons.csv. */
export interface InvolvedPerson {
  entity_id: string
  name: string | null
  phone: string | null
  home_city: string | null
  risk_group: string | null
}

/** One FIR row. `involved_person` is joined from persons.csv, or null. */
export interface CaseRecord {
  fir_id: string
  person_id: string | null
  crime: string | null
  date: string | null
  location: string | null
  ingested_at?: string | null
  involved_person: InvolvedPerson | null
}

/** `GET /cases`. */
export interface CaseListResponse {
  total: number
  data: CaseRecord[]
}

/** `GET /cases/{fir_id}`. Same join as the list item. */
export type CaseDetailResponse = CaseRecord

export type CaseLookup =
  | { found: true; case: CaseDetailResponse }
  | { found: false }

export interface CaseFilters {
  crime?: string
  location?: string
  person_id?: string
}

/** List-page filters. Crime and location map to backend query params. */
export interface CaseExplorerFilters {
  query: string
  crime: string
  location: string
}

export interface CaseRow {
  fir: CaseRecord
  involvedPerson: InvolvedPerson | null
  riskScore: number | null
  riskLevel: RiskLevel | null
}

export interface CaseSummary {
  total: number
  crimes: number
  locations: number
  people: number
}
