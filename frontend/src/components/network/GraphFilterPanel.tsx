import { Checkbox, Panel, PanelBody, PanelHeader } from '@/components/ui'
import { ENTITY_PRESENTATION, relationshipLabel } from '@/lib/entities'
import { formatNumber } from '@/lib/format'
import { ENTITY_TYPES } from '@/types'
import type { EntityType, GraphFilters, GraphIndex } from '@/types'

export interface GraphFilterPanelProps {
  index: GraphIndex
  filters: GraphFilters
  onEntityTypesChange: (types: ReadonlySet<EntityType>) => void
  onRelationshipsChange: (relationships: ReadonlySet<string>) => void
}

function toggle<T>(set: ReadonlySet<T>, value: T, checked: boolean): Set<T> {
  const next = new Set(set)
  if (checked) next.add(value)
  else next.delete(value)
  return next
}

/**
 * Visualisation-only filters. Nothing here is sent to the backend; the loaded
 * payload is simply shown or hidden.
 */
export function GraphFilterPanel({
  index,
  filters,
  onEntityTypesChange,
  onRelationshipsChange,
}: GraphFilterPanelProps) {
  const allEntityTypes = ENTITY_TYPES.every((type) =>
    filters.entityTypes.has(type),
  )
  const allRelationships = index.relationshipTypes.every((relationship) =>
    filters.relationships.has(relationship),
  )

  return (
    <Panel>
      <PanelHeader
        title="Filters"
        description="Show or hide parts of the loaded graph."
      />

      <PanelBody className="space-y-4 px-2.5 py-3">
        <div>
          <p className="mb-1 px-1.5 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
            Entity types
          </p>

          <Checkbox
            label="All entity types"
            checked={allEntityTypes}
            onChange={(checked) =>
              onEntityTypesChange(new Set(checked ? ENTITY_TYPES : []))
            }
          />

          <div className="mt-0.5 border-t border-line pt-0.5">
            {ENTITY_TYPES.map((type) => (
              <Checkbox
                key={type}
                label={ENTITY_PRESENTATION[type].label}
                swatchClass={ENTITY_PRESENTATION[type].dotClass}
                checked={filters.entityTypes.has(type)}
                detail={formatNumber(index.entityTypeCounts[type])}
                onChange={(checked) =>
                  onEntityTypesChange(
                    toggle(filters.entityTypes, type, checked),
                  )
                }
              />
            ))}
          </div>
        </div>

        <div>
          <p className="mb-1 px-1.5 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
            Relationships
          </p>

          <Checkbox
            label="All relationships"
            checked={allRelationships}
            onChange={(checked) =>
              onRelationshipsChange(
                new Set(checked ? index.relationshipTypes : []),
              )
            }
          />

          <div className="mt-0.5 border-t border-line pt-0.5">
            {index.relationshipTypes.map((relationship) => (
              <Checkbox
                key={relationship}
                label={relationshipLabel(relationship)}
                checked={filters.relationships.has(relationship)}
                detail={formatNumber(
                  index.relationshipCounts.get(relationship) ?? 0,
                )}
                onChange={(checked) =>
                  onRelationshipsChange(
                    toggle(filters.relationships, relationship, checked),
                  )
                }
              />
            ))}
          </div>
        </div>
      </PanelBody>
    </Panel>
  )
}
