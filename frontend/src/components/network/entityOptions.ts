import type { ComboboxOption } from '@/components/ui'
import { ENTITY_PRESENTATION } from '@/lib/entities'
import type { EntityOption } from '@/types'

/** Adapts a graph entity to the shared combobox option shape. */
export function toComboboxOption(option: EntityOption): ComboboxOption {
  return {
    id: option.id,
    label: option.label,
    detail: option.id,
    swatchClass: ENTITY_PRESENTATION[option.entityType].dotClass,
  }
}
