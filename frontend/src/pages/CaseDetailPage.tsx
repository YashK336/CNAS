import { ArrowLeft, RefreshCw, ScrollText, TriangleAlert } from 'lucide-react'
import { useParams } from 'react-router-dom'

import {
  CaseIdentificationPanel,
  CaseNetworkContextPanel,
  InvolvedPersonPanel,
} from '@/components/cases'
import { ReportExportButtons } from '@/components/reports'
import { RiskBadge } from '@/components/risk'
import {
  Badge,
  Button,
  EmptyState,
  LinkButton,
  Panel,
  PanelBody,
  SectionHeader,
  Skeleton,
} from '@/components/ui'
import { useCaseDetail } from '@/hooks'
import { formatText } from '@/lib/format'
import { cleanValue } from '@/lib/graph'

function BackToCases() {
  return (
    <LinkButton
      to="/cases"
      size="sm"
      icon={<ArrowLeft size={13} strokeWidth={1.75} />}
    >
      Back to Cases
    </LinkButton>
  )
}

function DetailSkeleton() {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      {Array.from({ length: 3 }, (_, index) => (
        <Panel key={index}>
          <PanelBody className="space-y-2.5">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-4/5" />
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-3 w-3/4" />
          </PanelBody>
        </Panel>
      ))}
    </div>
  )
}

export function CaseDetailPage() {
  const { firId = '' } = useParams<{ firId: string }>()
  const { record, row, notFound, reload } = useCaseDetail(firId)

  const header = (title: string, description?: string) => (
    <SectionHeader
      eyebrow="Case intelligence"
      title={title}
      description={description}
      actions={<BackToCases />}
    />
  )

  if (notFound) {
    return (
      <div className="space-y-4">
        {header('Case detail')}
        <Panel>
          <EmptyState
            icon={<ScrollText size={16} strokeWidth={1.75} />}
            title="Case not found."
            description={`No FIR with ID ${firId} exists in the current dataset.`}
            actions={<BackToCases />}
          />
        </Panel>
      </div>
    )
  }

  if (record.error !== null && !row) {
    return (
      <div className="space-y-4">
        {header('Case detail')}
        <Panel>
          <EmptyState
            icon={<TriangleAlert size={16} strokeWidth={1.75} />}
            title="Unable to load this case."
            description={record.error}
            actions={
              <>
                <Button
                  onClick={reload}
                  icon={<RefreshCw size={13} strokeWidth={1.75} />}
                >
                  Retry
                </Button>
                <BackToCases />
              </>
            }
          />
        </Panel>
      </div>
    )
  }

  if (!row) {
    return (
      <div className="space-y-4">
        {header('Loading case…')}
        <DetailSkeleton />
      </div>
    )
  }

  const personName = cleanValue(row.involvedPerson?.name)
  const location = cleanValue(row.fir.location)

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Case intelligence"
        title={formatText(row.fir.fir_id)}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">{formatText(row.fir.crime)}</Badge>
            {row.riskLevel ? (
              typeof row.riskScore === 'number' ? (
                <RiskBadge level={row.riskLevel} score={row.riskScore} />
              ) : (
                <RiskBadge level={row.riskLevel} />
              )
            ) : null}
            {personName ? (
              <span className="text-xs text-ink-muted">
                Involved person: {personName}
              </span>
            ) : null}
            {location ? (
              <span className="text-xs text-ink-muted">{location}</span>
            ) : null}
          </span>
        }
        actions={
          <>
            <ReportExportButtons source="case" id={row.fir.fir_id} />
            <BackToCases />
            <Button
              size="sm"
              variant="ghost"
              onClick={reload}
              aria-label="Reload case"
              title="Reload case"
              icon={
                <RefreshCw
                  size={13}
                  strokeWidth={1.75}
                  className={record.isLoading ? 'animate-spin' : undefined}
                />
              }
            />
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <CaseIdentificationPanel row={row} />
        <InvolvedPersonPanel row={row} />
        <CaseNetworkContextPanel row={row} />
      </div>
    </div>
  )
}
