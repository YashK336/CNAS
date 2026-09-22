import { http } from './api'
import type { RequestOptions } from './api'
import type { AuditLogListResponse } from '@/types'

export interface AuditLogQuery {
  limit?: number
  offset?: number
}

export function getAuditLogs(
  query: AuditLogQuery = {},
  options?: RequestOptions,
): Promise<AuditLogListResponse> {
  const params = new URLSearchParams()
  if (query.limit !== undefined) params.set('limit', String(query.limit))
  if (query.offset !== undefined) params.set('offset', String(query.offset))
  const suffix = params.size > 0 ? `?${params.toString()}` : ''
  return http.get<AuditLogListResponse>(`/audit/logs${suffix}`, options)
}
