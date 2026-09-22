import { ArrowRight, Crosshair, ExternalLink, MousePointer2 } from 'lucide-react'

import {
  Badge,
  Button,
  EmptyState,
  LinkButton,
  Panel,
  PanelBody,
  PanelHeader,
} from '@/components/ui'
import { ENTITY_PRESENTATION, relationshipLabel } from '@/lib/entities'
import {
  entityAttributes,
  entityPrimaryLabel,
  summariseEdgeRecords,
  summariseNodeRelationships,
} from '@/lib/graph'
import {
  EMPTY_VALUE,
  formatCurrency,
  formatDateTime,
  formatNumber,
} from '@/lib/format'
import type { AggregatedEdge, GraphIndex, GraphSelection, NetworkNode } from '@/types'

export interface EntityInspectorProps {
  index: GraphIndex
  selection: GraphSelection | null
  onSetTraceSource: (entityId: string) => void
  onSetTraceTarget: (entityId: string) => void
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <span className="shrink-0 text-2xs text-ink-faint">{label}</span>
      <span
        className={
          mono
            ? 'min-w-0 truncate text-right font-mono text-2xs text-ink'
            : 'min-w-0 truncate text-right text-xs text-ink'
        }
      >
        {value}
      </span>
    </div>
  )
}

function SubHeading({ children }: { children: string }) {
  return (
    <p className="mb-1 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
      {children}
    </p>
  )
}

function NodeDetails({
  index,
  node,
  onSetTraceSource,
  onSetTraceTarget,
}: {
  index: GraphIndex
  node: NetworkNode
  onSetTraceSource: (entityId: string) => void
  onSetTraceTarget: (entityId: string) => void
}) {
  const presentation = ENTITY_PRESENTATION[node.entity_type]
  const attributes = entityAttributes(node)
  const relationships = summariseNodeRelationships(index, node.id)
  const connections = index.neighborsById.get(node.id)?.size ?? 0

  return (
    <PanelBody className="space-y-4 p-3">
      <div>
        <Badge className={presentation.chipClass}>{presentation.label}</Badge>
        <p className="mt-2 text-sm font-semibold text-ink">
          {entityPrimaryLabel(node)}
        </p>
        <p className="font-mono text-2xs text-ink-faint">{node.id}</p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {node.entity_type === 'person' ? (
          <LinkButton
            to={`/people/${encodeURIComponent(node.id)}`}
            size="sm"
            variant="primary"
            className="grow"
          >
            <ExternalLink size={12} strokeWidth={1.75} />
            Open profile
          </LinkButton>
        ) : null}
        <Button size="sm" onClick={() => onSetTraceSource(node.id)}>
          Set as source
        </Button>
        <Button size="sm" onClick={() => onSetTraceTarget(node.id)}>
          Set as target
        </Button>
      </div>

      <div>
        <SubHeading>Attributes</SubHeading>
        <div className="divide-y divide-line">
          {attributes.map((attribute) => (
            <Row
              key={attribute.label}
              label={attribute.label}
              value={attribute.value}
              mono={attribute.mono ?? false}
            />
          ))}
        </div>
      </div>

      <div>
        <SubHeading>Connections</SubHeading>
        <div className="divide-y divide-line">
          <Row
            label="Connected entities"
            value={formatNumber(connections)}
            mono
          />
          {relationships.map((summary) => (
            <Row
              key={summary.relationship}
              label={relationshipLabel(summary.relationship)}
              value={`${formatNumber(summary.links)} · ${formatNumber(summary.interactions)}`}
              mono
            />
          ))}
        </div>
        {relationships.length > 0 ? (
          <p className="mt-1.5 text-2xs text-ink-faint">
            Links · underlying records per relationship.
          </p>
        ) : null}
      </div>
    </PanelBody>
  )
}

function EdgeDetails({
  index,
  edge,
}: {
  index: GraphIndex
  edge: AggregatedEdge
}) {
  const source = index.nodesById.get(edge.source)
  const target = index.nodesById.get(edge.target)
  const metadata = summariseEdgeRecords(edge)

  return (
    <PanelBody className="space-y-4 p-3">
      <div>
        <Badge tone="accent" mono>
          {edge.relationship}
        </Badge>
        <p className="mt-2 text-sm font-semibold text-ink">
          {relationshipLabel(edge.relationship)}
        </p>
        <p className="text-2xs text-ink-muted">
          {formatNumber(edge.count)}
          {edge.count === 1 ? ' interaction' : ' interactions'} between this pair
        </p>
      </div>

      <div className="space-y-1.5 rounded-sm border border-line bg-surface-raised p-2">
        <p className="truncate text-xs text-ink">
          {source ? entityPrimaryLabel(source) : edge.source}
          <span className="ml-1.5 font-mono text-2xs text-ink-faint">
            {edge.source}
          </span>
        </p>
        <p className="flex items-center gap-1 text-2xs text-accent">
          <ArrowRight size={11} strokeWidth={2} />
          {edge.relationship}
        </p>
        <p className="truncate text-xs text-ink">
          {target ? entityPrimaryLabel(target) : edge.target}
          <span className="ml-1.5 font-mono text-2xs text-ink-faint">
            {edge.target}
          </span>
        </p>
      </div>

      <div>
        <SubHeading>Aggregated metadata</SubHeading>
        <div className="divide-y divide-line">
          <Row label="Records" value={formatNumber(edge.count)} mono />
          {metadata.totalAmount !== null ? (
            <Row
              label="Total amount"
              value={formatCurrency(metadata.totalAmount)}
              mono
            />
          ) : null}
          {metadata.totalDurationSeconds !== null ? (
            <Row
              label="Total duration"
              value={`${formatNumber(metadata.totalDurationSeconds)} s`}
              mono
            />
          ) : null}
          {metadata.callTypes.map((callType) => (
            <Row
              key={callType.value}
              label={`Call type · ${callType.value}`}
              value={formatNumber(callType.count)}
              mono
            />
          ))}
          {metadata.earliest ? (
            <Row label="Earliest" value={formatDateTime(metadata.earliest)} />
          ) : null}
          {metadata.latest ? (
            <Row label="Latest" value={formatDateTime(metadata.latest)} />
          ) : null}
        </div>
        {metadata.totalAmount === null &&
        metadata.totalDurationSeconds === null &&
        metadata.earliest === null ? (
          <p className="mt-1.5 text-2xs text-ink-faint">
            The backend supplies no further attributes for this relationship
            type.
          </p>
        ) : null}
      </div>
    </PanelBody>
  )
}

/** Right-hand detail view for whichever element is selected on the canvas. */
export function EntityInspector({
  index,
  selection,
  onSetTraceSource,
  onSetTraceTarget,
}: EntityInspectorProps) {
  const node =
    selection?.kind === 'node' ? index.nodesById.get(selection.id) : undefined
  const edge =
    selection?.kind === 'edge' ? index.edgesById.get(selection.id) : undefined

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title={edge ? 'Relationship' : 'Entity'}
        icon={<Crosshair size={13} strokeWidth={1.75} />}
      />

      {node ? (
        <NodeDetails
          index={index}
          node={node}
          onSetTraceSource={onSetTraceSource}
          onSetTraceTarget={onSetTraceTarget}
        />
      ) : edge ? (
        <EdgeDetails index={index} edge={edge} />
      ) : (
        <EmptyState
          className="px-4 py-10"
          icon={<MousePointer2 size={16} strokeWidth={1.75} />}
          title="Select an entity"
          description="Select a node to inspect its attributes and relationships."
        />
      )}

      {selection && !node && !edge ? (
        <p className="border-t border-line px-3 py-2 text-2xs text-ink-faint">
          {EMPTY_VALUE} This element is no longer part of the loaded graph.
        </p>
      ) : null}
    </Panel>
  )
}
