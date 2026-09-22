import { ArrowDown, GitBranch, ShieldCheck } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  Badge,
  Button,
  EmptyState,
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { formatDateTime, formatText } from '@/lib/format'
import { fetchPersonRiskEvidence } from '@/services/neo4j'
import { isAbortError, toErrorMessage } from '@/services'
import type {
  GraphPathRelationship,
  GraphPropagationEvidence,
  PersonRiskEvidenceResponse,
} from '@/types'

export interface PersonRiskEvidencePanelProps {
  personId: string
  /** Seeds from graph-aware risk scoring, or URL query params. */
  defaultSeeds?: string[]
}

function parseSeedInput(raw: string): string[] {
  return raw
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function ProvenanceRow({
  relationship,
}: {
  relationship: GraphPathRelationship
}) {
  const provenance = relationship.provenance
  if (!provenance) {
    return (
      <p className="text-2xs text-ink-faint">No provenance recorded.</p>
    )
  }

  return (
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-0.5 text-2xs">
      <dt className="text-ink-faint">Source</dt>
      <dd className="truncate font-mono text-ink">{formatText(provenance.source)}</dd>
      <dt className="text-ink-faint">Ref</dt>
      <dd className="truncate font-mono text-ink">
        {formatText(provenance.source_ref)}
      </dd>
      <dt className="text-ink-faint">Hash</dt>
      <dd className="truncate font-mono text-ink">
        {formatText(provenance.content_hash)}
      </dd>
      <dt className="text-ink-faint">Ingested</dt>
      <dd className="text-ink">{formatDateTime(provenance.ingested_at)}</dd>
    </dl>
  )
}

function EvidenceChain({ chain }: { chain: GraphPropagationEvidence }) {
  const nodes = chain.nodes ?? []
  const relationships = chain.relationships ?? []

  if (!chain.found) {
    return (
      <div className="rounded-sm border border-line bg-surface-raised px-2 py-2">
        <div className="mb-1 flex items-center gap-2">
          <Badge tone="neutral" mono>
            {chain.seed_id}
          </Badge>
          <span className="text-2xs text-signal-medium">
            {chain.message ?? 'No graph path to this person.'}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-sm border border-line bg-surface-raised px-2 py-2">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge tone="accent" mono>
          Seed {chain.seed_id}
        </Badge>
        <span className="text-2xs text-ink-muted">
          {chain.degrees_of_separation ?? 0} hop
          {(chain.degrees_of_separation ?? 0) === 1 ? '' : 's'}
        </span>
      </div>

      <ol className="space-y-0">
        {nodes.map((node, position) => {
          const relationship = relationships[position]
          return (
            <li key={`${node.entity_id}-${position}`}>
              <div className="flex items-center gap-2 rounded-sm border border-line-strong bg-surface px-2 py-1.5">
                <span className="min-w-0 flex-1 truncate text-xs text-ink">
                  {formatText(node.name)}
                </span>
                <Badge tone="neutral" mono>
                  {node.entity_id}
                </Badge>
              </div>

              {relationship ? (
                <div className="space-y-1 py-1 pl-3">
                  <div className="flex items-center gap-1.5 text-2xs text-accent">
                    <ArrowDown size={11} strokeWidth={2} aria-hidden />
                    <span className="font-mono tracking-wide">
                      {relationship.type}
                    </span>
                    <span className="text-ink-faint">
                      {relationship.source} → {relationship.target}
                    </span>
                  </div>
                  <ProvenanceRow relationship={relationship} />
                </div>
              ) : null}
            </li>
          )
        })}
      </ol>
    </div>
  )
}

/**
 * Evidence chains from `GET /analytics/risk/{person_id}/evidence`, showing
 * graph propagation paths with relationship types and provenance.
 */
export function PersonRiskEvidencePanel({
  personId,
  defaultSeeds = [],
}: PersonRiskEvidencePanelProps) {
  const initialSeeds = useMemo(
    () => (defaultSeeds.length > 0 ? defaultSeeds.join(', ') : ''),
    [defaultSeeds],
  )
  const [seedInput, setSeedInput] = useState(initialSeeds)
  const [evidence, setEvidence] = useState<PersonRiskEvidenceResponse | null>(
    null,
  )
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setSeedInput(initialSeeds)
  }, [initialSeeds])

  const loadEvidence = useCallback(
    (seeds: string[], signal?: AbortSignal) => {
      if (seeds.length === 0) {
        setEvidence(null)
        setError(null)
        return Promise.resolve()
      }

      setIsLoading(true)
      setError(null)

      return fetchPersonRiskEvidence(
        personId,
        seeds,
        signal ? { signal } : undefined,
      )
        .then((result) => {
          if (signal?.aborted) return
          setEvidence(result)
        })
        .catch((loadError: unknown) => {
          if (isAbortError(loadError) || signal?.aborted) return
          setEvidence(null)
          setError(toErrorMessage(loadError))
        })
        .finally(() => {
          if (!signal?.aborted) setIsLoading(false)
        })
    },
    [personId],
  )

  useEffect(() => {
    if (defaultSeeds.length === 0) return
    const controller = new AbortController()
    void loadEvidence(defaultSeeds, controller.signal)
    return () => controller.abort()
  }, [defaultSeeds, loadEvidence])

  const chains = evidence?.evidence.graph_propagation ?? []

  return (
    <Panel>
      <PanelHeader
        title="Risk evidence"
        description="Graph propagation paths and provenance from /analytics/risk/evidence."
        icon={<ShieldCheck size={15} strokeWidth={1.75} />}
        actions={
          evidence ? (
            <Badge tone="accent">{chains.length} chain(s)</Badge>
          ) : null
        }
      />

      <PanelBody className="space-y-3 p-2.5">
        <div className="space-y-1">
          <label
            htmlFor={`risk-evidence-seeds-${personId}`}
            className="px-0.5 text-2xs text-ink-muted"
          >
            Graph seeds
          </label>
          <input
            id={`risk-evidence-seeds-${personId}`}
            type="text"
            value={seedInput}
            onChange={(event) => setSeedInput(event.target.value)}
            placeholder="P001, P002"
            className="h-8 w-full rounded-sm border border-line-strong bg-surface-raised px-2 text-xs text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none"
          />
        </div>

        <Button
          size="sm"
          variant="primary"
          className="w-full"
          disabled={isLoading || parseSeedInput(seedInput).length === 0}
          onClick={() => void loadEvidence(parseSeedInput(seedInput))}
          icon={<GitBranch size={13} strokeWidth={1.75} />}
        >
          {isLoading ? 'Loading evidence…' : 'Load evidence'}
        </Button>

        {error ? (
          <SectionError
            message={error}
            onRetry={() => void loadEvidence(parseSeedInput(seedInput))}
          />
        ) : isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : parseSeedInput(seedInput).length === 0 ? (
          <EmptyState
            title="Provide graph seeds."
            description="Comma-separated person IDs used as propagation seeds for evidence lookup."
          />
        ) : chains.length === 0 ? (
          <EmptyState
            title="No evidence loaded."
            description="Load evidence to inspect graph propagation paths."
          />
        ) : (
          <div className="space-y-2">
            {chains.map((chain) => (
              <EvidenceChain key={chain.seed_id} chain={chain} />
            ))}
          </div>
        )}
      </PanelBody>
    </Panel>
  )
}
