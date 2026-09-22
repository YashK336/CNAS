import { useCallback, useMemo } from 'react'

import {
  caseRecordResource,
  casesResource,
  riskProfilesResource,
} from '@/services'
import { buildCaseRows } from '@/lib/cases'
import type { CaseLookup, CaseRow, RiskProfile } from '@/types'
import { useAsyncResource } from './useAsyncResource'
import type { AsyncResource } from './useAsyncResource'

export interface CaseDetailData {
  record: AsyncResource<CaseLookup>
  risk: AsyncResource<RiskProfile[]>
  row: CaseRow | null
  notFound: boolean
  reload: () => void
}

/**
 * Loads one FIR from `/cases/{fir_id}` and maps risk from the shared
 * `/analytics/risk` list. Does not rebuild the network graph.
 */
export function useCaseDetail(firId: string): CaseDetailData {
  const record = useAsyncResource<CaseLookup>(
    (options) => caseRecordResource.for(firId).load(options),
    [firId],
  )

  const risk = useAsyncResource<RiskProfile[]>((options) =>
    riskProfilesResource.load(options),
  )

  const row = useMemo(() => {
    if (!record.data?.found) return null
    return buildCaseRows([record.data.case], risk.data)[0] ?? null
  }, [record.data, risk.data])

  const refetchRecord = record.refetch
  const refetchRisk = risk.refetch

  const reload = useCallback(() => {
    caseRecordResource.invalidate()
    casesResource.invalidate()
    riskProfilesResource.invalidate()
    refetchRecord()
    refetchRisk()
  }, [refetchRecord, refetchRisk])

  return {
    record,
    risk,
    row,
    notFound: record.data?.found === false,
    reload,
  }
}
