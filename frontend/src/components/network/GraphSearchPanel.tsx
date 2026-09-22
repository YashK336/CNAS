import { useCallback } from 'react'

import { Combobox, Panel, PanelBody } from '@/components/ui'
import { searchEntityOptions } from '@/lib/graph'
import type { EntityOption } from '@/types'
import { toComboboxOption } from './entityOptions'

export interface GraphSearchPanelProps {
  options: EntityOption[]
  onSelect: (entityId: string) => void
}

/** Graph-local lookup by name, entity id, vehicle number or event type. */
export function GraphSearchPanel({
  options,
  onSelect,
}: GraphSearchPanelProps) {
  const search = useCallback(
    (query: string) => searchEntityOptions(options, query).map(toComboboxOption),
    [options],
  )

  return (
    <Panel>
      <PanelBody className="p-2.5">
        <Combobox
          label="Find entity"
          placeholder="Name, ID, vehicle number…"
          search={search}
          selected={null}
          onSelect={(option) => onSelect(option.id)}
          emptyMessage="No entity matches this search"
        />
      </PanelBody>
    </Panel>
  )
}
