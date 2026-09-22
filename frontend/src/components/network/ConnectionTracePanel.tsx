import { Route } from 'lucide-react'
import { useCallback, useMemo } from 'react'

import { Button, Combobox, Panel, PanelBody, PanelHeader } from '@/components/ui'
import type { ComboboxOption } from '@/components/ui'
import { searchEntityOptions } from '@/lib/graph'
import type { EntityOption } from '@/types'
import { toComboboxOption } from './entityOptions'

export interface ConnectionTracePanelProps {
  options: EntityOption[]
  sourceId: string | null
  targetId: string | null
  onSourceChange: (entityId: string | null) => void
  onTargetChange: (entityId: string | null) => void
  onTrace: () => void
  isTracing: boolean
}

/** Picks the two endpoints for `GET /analytics/connection/{source}/{target}`. */
export function ConnectionTracePanel({
  options,
  sourceId,
  targetId,
  onSourceChange,
  onTargetChange,
  onTrace,
  isTracing,
}: ConnectionTracePanelProps) {
  const optionsById = useMemo(() => {
    const map = new Map<string, ComboboxOption>()
    for (const option of options) map.set(option.id, toComboboxOption(option))
    return map
  }, [options])

  const search = useCallback(
    (query: string) => searchEntityOptions(options, query).map(toComboboxOption),
    [options],
  )

  const ready = sourceId !== null && targetId !== null && sourceId !== targetId

  return (
    <Panel>
      <PanelHeader
        title="Connection trace"
        description="Shortest path between two entities in the backend graph."
      />

      <PanelBody className="space-y-3 p-2.5">
        <Combobox
          label="Source entity"
          search={search}
          selected={sourceId ? (optionsById.get(sourceId) ?? null) : null}
          onSelect={(option) => onSourceChange(option.id)}
          onClear={() => onSourceChange(null)}
        />

        <Combobox
          label="Target entity"
          search={search}
          selected={targetId ? (optionsById.get(targetId) ?? null) : null}
          onSelect={(option) => onTargetChange(option.id)}
          onClear={() => onTargetChange(null)}
        />

        <Button
          variant="primary"
          size="sm"
          className="w-full"
          disabled={!ready || isTracing}
          onClick={onTrace}
          icon={<Route size={13} strokeWidth={1.75} />}
        >
          {isTracing ? 'Tracing…' : 'Trace connection'}
        </Button>

        {sourceId !== null && sourceId === targetId ? (
          <p className="text-2xs text-signal-medium">
            Pick two different entities to trace.
          </p>
        ) : null}
      </PanelBody>
    </Panel>
  )
}
