import type { ReactNode } from 'react'

import {
  Badge,
  Panel,
  PanelBody,
  PanelHeader,
  SectionHeader,
} from '@/components/ui'

export interface ModulePlaceholderProps {
  eyebrow: string
  title: string
  description: string
  icon?: ReactNode
  /** Capabilities this module will provide once built. */
  planned: string[]
  /** Backend endpoints the module will consume. */
  endpoints?: string[]
  actions?: ReactNode
}

/**
 * Scaffold state for routed modules that are not implemented yet. It states
 * scope and the endpoints in play rather than rendering sample data.
 */
export function ModulePlaceholder({
  eyebrow,
  title,
  description,
  icon,
  planned,
  endpoints,
  actions,
}: ModulePlaceholderProps) {
  return (
    <div className="space-y-5">
      <SectionHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        actions={
          actions ?? <Badge tone="neutral">Not implemented yet</Badge>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Panel>
          <PanelHeader
            title="Planned capabilities"
            icon={icon}
            description="Scope agreed for this module. Nothing here is wired to data yet."
          />
          <PanelBody className="p-0">
            <ul className="divide-y divide-line">
              {planned.map((item, index) => (
                <li
                  key={item}
                  className="flex items-start gap-3 px-4 py-2.5 text-xs text-ink"
                >
                  <span className="mt-px w-4 shrink-0 font-mono text-2xs text-ink-faint tabular-nums">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          </PanelBody>
        </Panel>

        {endpoints && endpoints.length > 0 ? (
          <Panel>
            <PanelHeader
              title="Backend endpoints"
              description="Already available on the FastAPI service."
            />
            <PanelBody className="p-0">
              <ul className="divide-y divide-line">
                {endpoints.map((endpoint) => (
                  <li
                    key={endpoint}
                    className="flex items-center gap-2.5 px-4 py-2.5"
                  >
                    <span
                      aria-hidden
                      className="h-1 w-1 shrink-0 rounded-full bg-signal-low"
                    />
                    <code className="min-w-0 truncate font-mono text-2xs text-ink-muted">
                      {endpoint}
                    </code>
                  </li>
                ))}
              </ul>
            </PanelBody>
          </Panel>
        ) : null}
      </div>
    </div>
  )
}
