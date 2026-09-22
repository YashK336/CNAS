import { ClipboardList, RefreshCw, TriangleAlert } from 'lucide-react'

import { AuditLogTable } from '@/components/governance'
import { Button, EmptyState, LinkButton, Panel, SectionHeader } from '@/components/ui'
import { useAuditLog, useAuth } from '@/hooks'
import { formatNumber } from '@/lib/format'
import { isForbidden, isUnauthorized, toErrorMessage } from '@/services'

export function AuditLogPage() {
  const { canReadGovernance } = useAuth()
  const { audit, events, total, reload } = useAuditLog()

  if (!canReadGovernance) {
    return (
      <EmptyState
        icon={<ClipboardList size={16} strokeWidth={1.75} />}
        title="Insufficient permissions"
        description="Your account cannot access the audit log."
        actions={<LinkButton to="/">Return to dashboard</LinkButton>}
      />
    )
  }

  const loadFailed = audit.error !== null && events === null
  const errorMessage = audit.error ?? ''
  const unauthorized = isUnauthorized(audit.error) || /401|not authenticated/i.test(errorMessage)
  const forbidden = isForbidden(audit.error) || /403|insufficient permissions/i.test(errorMessage)

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Governance"
        title="Audit Log"
        description="Append-only record of authentication, authorization, investigation, and adjudication events."
        actions={
          <Button
            size="sm"
            onClick={reload}
            disabled={audit.isLoading}
            icon={
              <ClipboardList
                size={13}
                strokeWidth={1.75}
                className={audit.isLoading ? 'animate-pulse' : undefined}
              />
            }
          >
            {audit.isLoading ? 'Loading' : 'Reload'}
          </Button>
        }
      />

      <Panel>
        <div className="flex items-center justify-between border-b border-line px-3 py-2 text-2xs text-ink-muted">
          <span>{events ? `${formatNumber(total)} event(s)` : 'Loading…'}</span>
          <Button size="sm" variant="ghost" onClick={reload}>
            <RefreshCw size={13} strokeWidth={1.75} />
          </Button>
        </div>

        {loadFailed ? (
          <EmptyState
            icon={<TriangleAlert size={16} strokeWidth={1.75} />}
            title={
              unauthorized
                ? 'Authentication required'
                : forbidden
                  ? 'Access denied'
                  : 'Unable to load audit log.'
            }
            description={audit.error ? toErrorMessage(audit.error) : undefined}
            actions={
              unauthorized ? (
                <LinkButton to="/login" variant="primary">
                  Sign in
                </LinkButton>
              ) : (
                <Button
                  onClick={reload}
                  icon={<RefreshCw size={13} strokeWidth={1.75} />}
                >
                  Retry
                </Button>
              )
            }
          />
        ) : (
          <AuditLogTable events={events} isLoading={audit.isLoading} />
        )}
      </Panel>
    </div>
  )
}
