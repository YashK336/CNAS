/**
 * Pure derivations behind the Case Explorer.
 *
 * Identity and FIR fields come from `/cases`. Risk is mapped from a single
 * `/analytics/risk` payload — never fetched per row.
 */

import { cleanValue } from '@/lib/graph'
import type {
  CaseExplorerFilters,
  CaseRecord,
  CaseRow,
  CaseSummary,
  RiskProfile,
} from '@/types'

export function uniqueSorted(values: Array<string | null | undefined>): string[] {
  const seen = new Set<string>()

  for (const value of values) {
    const cleaned = cleanValue(value)
    if (cleaned) seen.add(cleaned)
  }

  return [...seen].sort((a, b) => a.localeCompare(b))
}

export function caseSummary(cases: CaseRecord[]): CaseSummary {
  const people = new Set<string>()

  for (const record of cases) {
    const personId =
      cleanValue(record.involved_person?.entity_id) ??
      cleanValue(record.person_id)
    if (personId) people.add(personId)
  }

  return {
    total: cases.length,
    crimes: uniqueSorted(cases.map((record) => record.crime)).length,
    locations: uniqueSorted(cases.map((record) => record.location)).length,
    people: people.size,
  }
}

/**
 * Joins each FIR to the risk profile of its involved person.
 *
 * `riskProfiles === null` means `/analytics/risk` has not settled yet, so the
 * risk cells stay empty rather than showing invented values.
 */
export function buildCaseRows(
  cases: CaseRecord[],
  riskProfiles: RiskProfile[] | null,
): CaseRow[] {
  const riskById = new Map<string, RiskProfile>()

  for (const profile of riskProfiles ?? []) {
    riskById.set(String(profile.entity_id), profile)
  }

  return cases.map((fir) => {
    const personId =
      cleanValue(fir.involved_person?.entity_id) ?? cleanValue(fir.person_id)
    const risk = personId ? (riskById.get(personId) ?? null) : null

    return {
      fir,
      involvedPerson: fir.involved_person,
      riskScore: risk?.risk_score ?? null,
      riskLevel: risk?.risk_level ?? null,
    }
  })
}

function matchesQuery(row: CaseRow, query: string): boolean {
  const needle = query.trim().toLowerCase()
  if (needle === '') return true

  const haystack = [
    row.fir.fir_id,
    row.fir.crime,
    row.fir.location,
    row.fir.person_id,
    row.involvedPerson?.entity_id,
    row.involvedPerson?.name,
  ]

  return haystack.some((value) => {
    const text = cleanValue(value)
    return text !== null && text.toLowerCase().includes(needle)
  })
}

function matchesExact(
  value: string | null | undefined,
  selected: string,
): boolean {
  const needle = selected.trim().toLowerCase()
  if (needle === '') return true

  const text = cleanValue(value)
  return text !== null && text.toLowerCase() === needle
}

export function filterCaseRows(
  rows: CaseRow[],
  filters: CaseExplorerFilters,
): CaseRow[] {
  return rows.filter(
    (row) =>
      matchesQuery(row, filters.query) &&
      matchesExact(row.fir.crime, filters.crime) &&
      matchesExact(row.fir.location, filters.location),
  )
}

export const EMPTY_CASE_FILTERS: CaseExplorerFilters = {
  query: '',
  crime: '',
  location: '',
}

export function hasActiveCaseFilters(filters: CaseExplorerFilters): boolean {
  return (
    filters.query.trim() !== '' ||
    filters.crime.trim() !== '' ||
    filters.location.trim() !== ''
  )
}
