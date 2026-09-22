import { getInvestigations } from '@/services'
import type { SavedInvestigationListResponse } from '@/types'
import { useAsyncResource } from './useAsyncResource'

export function useInvestigations() {
  const investigations = useAsyncResource<SavedInvestigationListResponse>(
    (options) => getInvestigations(options),
    [],
  )

  return {
    investigations,
    records: investigations.data?.data ?? null,
    total: investigations.data?.total ?? 0,
    reload: investigations.refetch,
  }
}
