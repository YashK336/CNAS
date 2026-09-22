import { getAuditLogs } from '@/services'
import type { AuditLogListResponse } from '@/types'
import { useAsyncResource } from './useAsyncResource'

export function useAuditLog(limit = 100) {
  const audit = useAsyncResource<AuditLogListResponse>(
    (options) => getAuditLogs({ limit }, options),
    [limit],
  )

  return {
    audit,
    events: audit.data?.events ?? null,
    total: audit.data?.total ?? 0,
    reload: audit.refetch,
  }
}
