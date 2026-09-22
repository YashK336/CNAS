import { useCallback, useMemo } from 'react'

import { caseSummary, buildCaseRows } from '@/lib/cases'
import {
  casesResource,
  riskProfilesResource,
} from '@/services'
import type { CaseRecord, CaseRow, CaseSummary, RiskProfile } from '@/types'
import { useAsyncResource } from './useAsyncResource'
import type { AsyncResource } from './useAsyncResource'

export interface CasesExplorer {
  cases: AsyncResource<CaseRecord[]>
  risk: AsyncResource<RiskProfile[]>
  /** Joined rows; null until `/cases` has resolved. */
  rows: CaseRow[] | null
  summary: CaseSummary | null
  lastLoadedAt: Date | null
  reload: () => void
}

/**
 * Loads the FIR register and a single risk payload in parallel.
 *
 * Risk is mapped locally by person id so the table never calls `/analytics/risk`
 * per row. Both lists are session-cached; `reload` is the only refetch.
 */
export function useCasesExplorer(): CasesExplorer {
  const cases = useAsyncResource<CaseRecord[]>((options) =>
    casesResource.load(options),
  )

  const risk = useAsyncResource<RiskProfile[]>((options) =>
    riskProfilesResource.load(options),
  )

  const rows = useMemo(
    () => (cases.data ? buildCaseRows(cases.data, risk.data) : null),
    [cases.data, risk.data],
  )

  const summary = useMemo(
    () => (cases.data ? caseSummary(cases.data) : null),
    [cases.data],
  )

  const settledTimes = [cases, risk]
    .map((resource) => resource.settledAt?.getTime())
    .filter((time): time is number => time !== undefined)

  const lastLoadedAt =
    settledTimes.length > 0 ? new Date(Math.max(...settledTimes)) : null

  const refetchCases = cases.refetch
  const refetchRisk = risk.refetch

  const reload = useCallback(() => {
    casesResource.invalidate()
    riskProfilesResource.invalidate()
    refetchCases()
    refetchRisk()
  }, [refetchCases, refetchRisk])

  return { cases, risk, rows, summary, lastLoadedAt, reload }
}
