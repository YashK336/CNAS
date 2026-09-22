/** Append-only audit event from `/audit/logs`. */

export interface AuditLogEvent {
  id: string
  timestamp: string
  actor_id: string | null
  actor_username: string | null
  action: string
  resource_type: string
  resource_id: string | null
  jurisdiction: string | null
  result: 'success' | 'denied' | 'failure'
  metadata: Record<string, unknown>
}

export interface AuditLogListResponse {
  total: number
  events: AuditLogEvent[]
}
