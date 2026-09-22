import { ArrowLeft, RefreshCw, TriangleAlert, UserX } from 'lucide-react'
import { useMemo } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'

import {
  AssociatedEntitiesPanel,
  ConnectionSummaryPanel,
  NetworkImportancePanel,
  PersonActivityPanel,
  PersonNetworkPanel,
  PersonOverviewPanel,
  PersonRiskEvidencePanel,
  PersonRiskPanel,
} from '@/components/people'
import { PersonAnomalyPanel } from '@/components/anomaly'
import type { MetricStatus } from '@/components/people'
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
import { usePersonProfile } from '@/hooks'
import { formatText } from '@/lib/format'
import { cleanValue } from '@/lib/graph'

function BackToPeople() {
  return (
    <LinkButton
      to="/people"
      size="sm"
      icon={<ArrowLeft size={13} strokeWidth={1.75} />}
    >
      Back to People
    </LinkButton>
  )
}

function ProfileSkeleton() {
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

export function PersonDetailPage() {
  const { personId = '' } = useParams<{ personId: string }>()
  const [searchParams] = useSearchParams()
  const { person, risk, anomaly, centrality, graph, profile, notFound, reload } =
    usePersonProfile(personId)

  const evidenceSeeds = useMemo(() => {
    const fromQuery = searchParams.get('graph_seeds')
    if (fromQuery) {
      return fromQuery
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    }
    return profile?.risk?.graph_seeds ?? []
  }, [searchParams, profile?.risk?.graph_seeds])

  const header = (title: string, description?: string) => (
    <SectionHeader
      eyebrow="Entity intelligence"
      title={title}
      description={description}
      actions={<BackToPeople />}
    />
  )

  if (notFound) {
    return (
      <div className="space-y-4">
        {header('Person profile')}
        <Panel>
          <EmptyState
            icon={<UserX size={16} strokeWidth={1.75} />}
            title="Person not found."
            description={`No person with ID ${personId} exists in the current dataset.`}
            actions={<BackToPeople />}
          />
        </Panel>
      </div>
    )
  }

  if (person.error !== null && !profile) {
    return (
      <div className="space-y-4">
        {header('Person profile')}
        <Panel>
          <EmptyState
            icon={<TriangleAlert size={16} strokeWidth={1.75} />}
            title="Unable to load this person."
            description={person.error}
            actions={
              <>
                <Button
                  onClick={reload}
                  icon={<RefreshCw size={13} strokeWidth={1.75} />}
                >
                  Retry
                </Button>
                <BackToPeople />
              </>
            }
          />
        </Panel>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="space-y-4">
        {header('Loading person profile…')}
        <ProfileSkeleton />
      </div>
    )
  }

  const homeCity = cleanValue(profile.person.home_city)
  const graphError = graph.error

  const centralityStatus: MetricStatus = centrality.data
    ? 'ready'
    : centrality.error
      ? 'error'
      : 'loading'

  const graphStatus: MetricStatus = profile.graph
    ? 'ready'
    : graphError
      ? 'error'
      : 'loading'

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Person profile"
        title={formatText(profile.person.name)}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <Badge tone="accent" mono>
              {profile.personId}
            </Badge>
            {profile.risk ? (
              <RiskBadge
                level={profile.risk.risk_level}
                score={profile.risk.risk_score}
              />
            ) : null}
            {homeCity ? (
              <span className="text-xs text-ink-muted">{homeCity}</span>
            ) : null}
          </span>
        }
        actions={
          <>
            <LinkButton
              to={`/network?focus=${encodeURIComponent(profile.personId)}`}
              size="sm"
              variant="primary"
            >
              Open in Network
            </LinkButton>
            <BackToPeople />
            <Button
              size="sm"
              variant="ghost"
              onClick={reload}
              aria-label="Reload profile"
              title="Reload profile"
              icon={
                <RefreshCw
                  size={13}
                  strokeWidth={1.75}
                  className={graph.isLoading ? 'animate-spin' : undefined}
                />
              }
            />
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <PersonOverviewPanel person={profile.person} />

        <NetworkImportancePanel
          centrality={profile.centrality}
          centralityStatus={centralityStatus}
          directConnections={profile.graph?.directConnections ?? null}
          graphStatus={graphStatus}
        />

        <PersonRiskPanel
          risk={profile.risk}
          isLoading={risk.isLoading}
          error={risk.error}
          onRetry={reload}
        />
      </div>

      <PersonRiskEvidencePanel
        personId={profile.personId}
        defaultSeeds={evidenceSeeds}
      />

      <PersonAnomalyPanel
        anomaly={profile.anomaly}
        isLoading={anomaly.isLoading}
        error={anomaly.error}
        onRetry={reload}
      />

      <ConnectionSummaryPanel
        counts={profile.graph?.relationshipCounts ?? null}
        isLoading={graph.isLoading}
        error={graphError}
        onRetry={reload}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <AssociatedEntitiesPanel
          associations={profile.graph?.associations ?? null}
          isLoading={graph.isLoading}
          error={graphError}
          onRetry={reload}
        />

        {/* `self-start`: the feed is capped, so stretching it to match the
            association columns would leave an empty panel tail. */}
        <div className="self-start">
          <PersonActivityPanel
            activity={profile.graph?.activity ?? null}
            isLoading={graph.isLoading}
            error={graphError}
            onRetry={reload}
          />
        </div>
      </div>

      {/* Full width: a local graph in a side column zooms out too far for the
          node labels to stay legible. */}
      <PersonNetworkPanel
        personId={profile.personId}
        neighbourhood={profile.graph?.neighbourhood ?? null}
        error={graphError}
        onRetry={reload}
      />
    </div>
  )
}
