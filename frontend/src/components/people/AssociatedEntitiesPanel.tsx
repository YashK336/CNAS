import {
  Banknote,
  Car,
  Cctv,
  MessagesSquare,
  Network,
  PhoneCall,
  ScrollText,
  Users,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import {
  Badge,
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import {
  EMPTY_VALUE,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatDuration,
  formatNumber,
} from '@/lib/format'
import { cleanValue } from '@/lib/graph'
import type {
  ConnectedPerson,
  NetworkNode,
  PersonAssociations,
  PersonRelationship,
} from '@/types'
import { AssociationSection } from './AssociationSection'

const ICON = { size: 12, strokeWidth: 1.75 } as const

function relationshipText(relationship: string): string {
  return relationship.replaceAll('_', ' ')
}

function plural(count: number, singular: string): string {
  return `${formatNumber(count)} ${singular}${count === 1 ? '' : 's'}`
}

/** Secondary line for a counterpart, built only from attributes it carries. */
function counterpartMeta(node: NetworkNode | null): string | null {
  if (!node) return null

  const parts: (string | null)[] = []

  switch (node.entity_type) {
    case 'person':
      parts.push(cleanValue(node.home_city), cleanValue(node.phone))
      break
    case 'vehicle':
      parts.push(
        cleanValue(node.vehicle_type),
        cleanValue(node.registered_city),
      )
      break
    case 'crime_event':
      parts.push(
        cleanValue(node.crime),
        cleanValue(node.location),
        cleanValue(node.date) ? formatDate(node.date) : null,
      )
      break
    case 'surveillance_event':
      parts.push(
        cleanValue(node.event_type),
        cleanValue(node.location),
        cleanValue(node.timestamp) ? formatDateTime(node.timestamp) : null,
      )
      break
  }

  const kept = parts.filter(
    (part): part is string => part !== null && part !== EMPTY_VALUE,
  )

  return kept.length > 0 ? kept.join(' · ') : null
}

function Row({ to, children }: { to?: string; children: ReactNode }) {
  return (
    <li>
      {to ? (
        <Link
          to={to}
          className="block px-3 py-2 transition-colors hover:bg-surface-hover"
        >
          {children}
        </Link>
      ) : (
        <div className="px-3 py-2">{children}</div>
      )}
    </li>
  )
}

function Direction({ outgoing }: { outgoing: boolean }) {
  return (
    <span
      title={outgoing ? 'From this person' : 'To this person'}
      className="shrink-0 font-mono text-2xs text-ink-faint"
    >
      {outgoing ? '→' : '←'}
      <span className="sr-only">{outgoing ? 'outgoing' : 'incoming'}</span>
    </span>
  )
}

function MetaLine({ children }: { children: ReactNode }) {
  return (
    <p className="mt-0.5 flex flex-wrap items-baseline gap-x-2 text-2xs text-ink-muted">
      {children}
    </p>
  )
}

/** Vehicles, FIRs and surveillance events: identified by their node id. */
function EntityRow({ link }: { link: PersonRelationship }) {
  const meta = counterpartMeta(link.counterpart)

  return (
    <Row>
      <div className="flex items-baseline gap-2">
        <span className="min-w-0 flex-1 truncate font-mono text-xs text-ink">
          {link.counterpartId}
        </span>
        <span className="shrink-0 text-2xs tracking-wide text-ink-faint uppercase">
          {relationshipText(link.relationship)}
        </span>
      </div>
      {meta ? <MetaLine>{meta}</MetaLine> : null}
    </Row>
  )
}

function ConnectedPersonRow({ person }: { person: ConnectedPerson }) {
  return (
    <Row to={`/people/${encodeURIComponent(person.entityId)}`}>
      <div className="flex items-baseline gap-2">
        <span className="min-w-0 flex-1 truncate text-xs text-ink">
          {person.name}
        </span>
        <span className="shrink-0 font-mono text-2xs text-accent">
          {person.entityId}
        </span>
      </div>
      <MetaLine>
        <span>{plural(person.interactions, 'record')}</span>
        {person.homeCity ? <span>{person.homeCity}</span> : null}
      </MetaLine>
      <div className="mt-1 flex flex-wrap gap-1">
        {person.relationships.map((relationship) => (
          <Badge key={relationship} mono className="text-[10px]">
            {relationshipText(relationship)}
          </Badge>
        ))}
      </div>
    </Row>
  )
}

function TransferRow({ link }: { link: PersonRelationship }) {
  return (
    <Row to={`/people/${encodeURIComponent(link.counterpartId)}`}>
      <div className="flex items-baseline gap-1.5">
        <Direction outgoing={link.outgoing} />
        <span className="min-w-0 flex-1 truncate text-xs text-ink">
          {link.counterpartLabel}
        </span>
        <span className="shrink-0 font-mono text-2xs text-accent">
          {link.counterpartId}
        </span>
      </div>
      <MetaLine>
        {link.totalAmount === null ? null : (
          <span className="font-mono text-ink">
            {formatCurrency(link.totalAmount)}
          </span>
        )}
        <span>{plural(link.count, 'transfer')}</span>
        {link.latest ? <span>{formatDate(link.latest)}</span> : null}
      </MetaLine>
    </Row>
  )
}

function CallRow({ link }: { link: PersonRelationship }) {
  return (
    <Row to={`/people/${encodeURIComponent(link.counterpartId)}`}>
      <div className="flex items-baseline gap-1.5">
        <Direction outgoing={link.outgoing} />
        <span className="min-w-0 flex-1 truncate text-xs text-ink">
          {link.counterpartLabel}
        </span>
        <span className="shrink-0 font-mono text-2xs text-accent">
          {link.counterpartId}
        </span>
      </div>
      <MetaLine>
        <span>{plural(link.count, 'call')}</span>
        {link.totalDurationSeconds === null ? null : (
          <span className="font-mono">
            {formatDuration(link.totalDurationSeconds)}
          </span>
        )}
        {link.latest ? <span>{formatDateTime(link.latest)}</span> : null}
      </MetaLine>
    </Row>
  )
}

function SocialRow({ link }: { link: PersonRelationship }) {
  return (
    <Row to={`/people/${encodeURIComponent(link.counterpartId)}`}>
      <div className="flex items-baseline gap-1.5">
        <Direction outgoing={link.outgoing} />
        <span className="min-w-0 flex-1 truncate text-xs text-ink">
          {link.counterpartLabel}
        </span>
        <span className="shrink-0 font-mono text-2xs text-accent">
          {link.counterpartId}
        </span>
      </div>
      <MetaLine>
        <span className="tracking-wide uppercase">
          {relationshipText(link.relationship)}
        </span>
        <span>{plural(link.count, 'interaction')}</span>
        {link.latest ? <span>{formatDate(link.latest)}</span> : null}
      </MetaLine>
    </Row>
  )
}

export interface AssociatedEntitiesPanelProps {
  /** Null while `/network/graph` is loading or after it failed. */
  associations: PersonAssociations | null
  isLoading: boolean
  error: string | null
  onRetry: () => void
}

/**
 * Every entity linked to this person in `/network/graph`, grouped by what the
 * link is. Direction and record counts come straight from the aggregated
 * backend edges.
 */
export function AssociatedEntitiesPanel({
  associations,
  isLoading,
  error,
  onRetry,
}: AssociatedEntitiesPanelProps) {
  return (
    <Panel>
      <PanelHeader
        title="Associated entities"
        description="Relationships derived from the /network/graph nodes and edges touching this person."
        icon={<Network size={15} strokeWidth={1.75} />}
      />

      {error && !associations ? (
        <SectionError message={error} onRetry={onRetry} />
      ) : !associations ? (
        <PanelBody className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 6 }, (_, index) => (
            <div
              key={index}
              className="space-y-2 rounded-md border border-line bg-surface-raised p-3"
            >
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          ))}
          {isLoading ? (
            <span className="sr-only">Loading associated entities</span>
          ) : null}
        </PanelBody>
      ) : (
        <PanelBody className="grid gap-3 md:grid-cols-2">
          <AssociationSection
            title="Vehicles"
            icon={<Car {...ICON} />}
            count={associations.vehicles.length}
            emptyMessage="No vehicle is linked to this person in the graph."
          >
            {associations.vehicles.map((link) => (
              <EntityRow key={link.id} link={link} />
            ))}
          </AssociationSection>

          <AssociationSection
            title="Crime events / FIRs"
            icon={<ScrollText {...ICON} />}
            count={associations.crimeEvents.length}
            emptyMessage="No FIR links this person to a crime event."
          >
            {associations.crimeEvents.map((link) => (
              <EntityRow key={link.id} link={link} />
            ))}
          </AssociationSection>

          <AssociationSection
            title="Surveillance events"
            icon={<Cctv {...ICON} />}
            count={associations.surveillance.length}
            emptyMessage="No surveillance observation is linked to this person."
          >
            {associations.surveillance.map((link) => (
              <EntityRow key={link.id} link={link} />
            ))}
          </AssociationSection>

          <AssociationSection
            title="Connected people"
            icon={<Users {...ICON} />}
            count={associations.connectedPeople.length}
            emptyMessage="No person-to-person link in the graph."
          >
            {associations.connectedPeople.map((person) => (
              <ConnectedPersonRow key={person.entityId} person={person} />
            ))}
          </AssociationSection>

          <AssociationSection
            title="Financial connections"
            icon={<Banknote {...ICON} />}
            count={associations.financial.length}
            emptyMessage="No money transfer involves this person."
          >
            {associations.financial.map((link) => (
              <TransferRow key={link.id} link={link} />
            ))}
          </AssociationSection>

          <AssociationSection
            title="Call connections"
            icon={<PhoneCall {...ICON} />}
            count={associations.calls.length}
            emptyMessage="No call detail record involves this person."
          >
            {associations.calls.map((link) => (
              <CallRow key={link.id} link={link} />
            ))}
          </AssociationSection>

          <AssociationSection
            title="Social connections"
            icon={<MessagesSquare {...ICON} />}
            count={associations.social.length}
            emptyMessage="No social interaction involves this person."
          >
            {associations.social.map((link) => (
              <SocialRow key={link.id} link={link} />
            ))}
          </AssociationSection>
        </PanelBody>
      )}
    </Panel>
  )
}
