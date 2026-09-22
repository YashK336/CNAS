import { CalendarRange, RotateCcw } from 'lucide-react'
import { useId } from 'react'

import { Badge, Button, Panel, PanelBody, PanelHeader } from '@/components/ui'
import { formatDateTime } from '@/lib/format'
import type { TemporalWindow } from '@/services/neo4j'

export interface GraphTemporalFilterPanelProps {
  draftFrom: string
  draftTo: string
  appliedWindow: TemporalWindow
  onDraftFromChange: (value: string) => void
  onDraftToChange: (value: string) => void
  onApply: () => void
  onClear: () => void
}

const INPUT_CLASS =
  'h-8 w-full rounded-sm border border-line-strong bg-surface-raised px-2 text-xs text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none'

/**
 * Draft from/to inputs for Neo4j temporal graph investigation. Values are sent
 * to the backend only after Apply is clicked.
 */
export function GraphTemporalFilterPanel({
  draftFrom,
  draftTo,
  appliedWindow,
  onDraftFromChange,
  onDraftToChange,
  onApply,
  onClear,
}: GraphTemporalFilterPanelProps) {
  const fromId = useId()
  const toId = useId()
  const windowActive =
    appliedWindow.fromDatetime !== null || appliedWindow.toDatetime !== null

  return (
    <Panel>
      <PanelHeader
        title="Temporal window"
        description="Restrict Neo4j path traces and GDS analytics to a time range."
        icon={<CalendarRange size={15} strokeWidth={1.75} />}
        actions={
          windowActive ? (
            <Badge tone="accent" mono>
              Active
            </Badge>
          ) : null
        }
      />

      <PanelBody className="space-y-3 p-2.5">
        <div className="space-y-1">
          <label htmlFor={fromId} className="px-0.5 text-2xs text-ink-muted">
            From
          </label>
          <input
            id={fromId}
            type="datetime-local"
            value={draftFrom}
            onChange={(event) => onDraftFromChange(event.target.value)}
            className={INPUT_CLASS}
          />
        </div>

        <div className="space-y-1">
          <label htmlFor={toId} className="px-0.5 text-2xs text-ink-muted">
            To
          </label>
          <input
            id={toId}
            type="datetime-local"
            value={draftTo}
            onChange={(event) => onDraftToChange(event.target.value)}
            className={INPUT_CLASS}
          />
        </div>

        {windowActive ? (
          <p className="rounded-sm border border-line bg-surface-raised px-2 py-1.5 text-2xs text-ink-muted">
            Applied:{' '}
            <span className="text-ink">
              {formatDateTime(appliedWindow.fromDatetime)} →{' '}
              {formatDateTime(appliedWindow.toDatetime)}
            </span>
          </p>
        ) : null}

        <div className="flex gap-2">
          <Button
            variant="primary"
            size="sm"
            className="flex-1"
            onClick={onApply}
          >
            Apply window
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onClear}
            disabled={!windowActive && draftFrom === '' && draftTo === ''}
            icon={<RotateCcw size={13} strokeWidth={1.75} />}
            aria-label="Clear temporal window"
            title="Clear temporal window"
          />
        </div>
      </PanelBody>
    </Panel>
  )
}

/** Convert a datetime-local control value to the backend query format. */
export function toApiDatetime(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  return trimmed.length === 16 ? `${trimmed}:00` : trimmed
}

/** Reverse mapping for repopulating draft inputs from an applied window. */
export function toDatetimeLocalValue(value: string | null): string {
  if (!value) return ''
  return value.slice(0, 16)
}
