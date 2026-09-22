import type { EntityType } from '@/types'

interface EntityPresentation {
  label: string
  /** Node/marker colour used by graph and legend surfaces. */
  dotClass: string
  chipClass: string
}

export const ENTITY_PRESENTATION: Record<EntityType, EntityPresentation> = {
  person: {
    label: 'Person',
    dotClass: 'bg-accent',
    chipClass: 'border-accent/35 bg-accent-muted text-accent',
  },
  vehicle: {
    label: 'Vehicle',
    dotClass: 'bg-ink-muted',
    chipClass: 'border-line-strong bg-surface-raised text-ink-muted',
  },
  crime_event: {
    label: 'Crime event',
    dotClass: 'bg-signal-critical',
    chipClass:
      'border-signal-critical/35 bg-signal-critical/10 text-signal-critical',
  },
  surveillance_event: {
    label: 'Surveillance event',
    dotClass: 'bg-signal-medium',
    chipClass:
      'border-signal-medium/35 bg-signal-medium/10 text-signal-medium',
  },
}

/** Known relationship labels emitted by the graph builder. */
export const RELATIONSHIP_LABELS: Record<string, string> = {
  OWNS: 'Owns',
  CALLED: 'Called',
  TRANSFERRED_MONEY: 'Transferred money',
  INVOLVED_IN: 'Involved in',
  OBSERVED_AT: 'Observed at',
}

export function relationshipLabel(relationship: string | null): string {
  if (!relationship) return 'Related to'

  const known = RELATIONSHIP_LABELS[relationship]
  if (known) return known

  if (relationship.startsWith('SOCIAL_')) {
    const interaction = relationship.slice('SOCIAL_'.length).toLowerCase()
    return `Social ${interaction}`
  }

  return relationship.replaceAll('_', ' ').toLowerCase()
}
