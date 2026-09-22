import { Bookmark, RefreshCw, TriangleAlert } from 'lucide-react'

import { InvestigationsTable } from '@/components/investigations'
import {
  Button,
  EmptyState,
  LinkButton,
  Panel,
  SectionHeader,
} from '@/components/ui'
import { useInvestigations } from '@/hooks'
import { formatNumber } from '@/lib/format'
import { toErrorMessage } from '@/services'

export function InvestigationsPage() {
  const { investigations, records, total, reload } = useInvestigations()
  const loadFailed = investigations.error !== null && records === null
  const errorMessage = investigations.error ?? ''
  const unauthorized = /401|not authenticated/i.test(errorMessage)
  const forbidden = /403|insufficient permissions/i.test(errorMessage)

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Investigation workspace"
        title="Saved Investigations"
        description="Resume Network Explorer sessions with saved entity selections, seeds and temporal windows."
        actions={
          <Button
            size="sm"
            onClick={reload}
            disabled={investigations.isLoading}
            icon={
              <Bookmark
                size={13}
                strokeWidth={1.75}
                className={investigations.isLoading ? 'animate-pulse' : undefined}
              />
            }
          >
            {investigations.isLoading ? 'Loading' : 'Reload'}
          </Button>
        }
      />

      <Panel>
        <div className="flex items-center justify-between border-b border-line px-3 py-2 text-2xs text-ink-muted">
          <span>
            {records ? `${formatNumber(total)} saved investigation(s)` : 'Loading…'}
          </span>
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
                  : 'Unable to load saved investigations.'
            }
            description={
              investigations.error
                ? toErrorMessage(investigations.error)
                : undefined
            }
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
          <InvestigationsTable
            records={records}
            isLoading={investigations.isLoading}
          />
        )}
      </Panel>
    </div>
  )
}
