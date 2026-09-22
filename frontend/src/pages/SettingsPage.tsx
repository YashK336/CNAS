import { RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'

import { RiskBadge } from '@/components/risk'
import { AppearanceToggle } from '@/components/settings'
import {
  Button,
  Panel,
  PanelBody,
  PanelHeader,
  SectionHeader,
  StatusIndicator,
} from '@/components/ui'
import type { StatusTone } from '@/components/ui'
import { useBackendStatus, useTheme } from '@/hooks'
import type { BackendStatus } from '@/hooks'
import { RISK_LEVEL_RANGE } from '@/lib/risk'
import { API_BASE_URL, REQUEST_TIMEOUT_MS } from '@/services'
import { RISK_LEVELS } from '@/types'

const TONE_BY_STATUS: Record<BackendStatus, StatusTone> = {
  checking: 'pending',
  online: 'online',
  offline: 'offline',
}

const LABEL_BY_STATUS: Record<BackendStatus, string> = {
  checking: 'Checking',
  online: 'Reachable',
  offline: 'Unreachable',
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-2.5">
      <span className="text-xs text-ink-muted">{label}</span>
      <span className="min-w-0 truncate text-right text-xs text-ink">
        {children}
      </span>
    </div>
  )
}

export function SettingsPage() {
  const { status, latencyMs, checkedAt, message, recheck } = useBackendStatus()
  const { theme } = useTheme()

  const baseUrlSource = import.meta.env.VITE_API_BASE_URL
    ? 'VITE_API_BASE_URL'
    : 'built-in fallback'

  return (
    <div className="space-y-5">
      <SectionHeader
        eyebrow="Configuration"
        title="Settings"
        description="Appearance for this workstation, plus live backend reachability and the risk-band thresholds the rule engine applies."
      />

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel>
          <PanelHeader
            title="Appearance"
            description="Applies across the workstation. Preference is stored in this browser and is not tied to your account."
          />
          <PanelBody className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-medium text-ink">Color theme</p>
              <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                Currently using the{' '}
                <span className="font-semibold text-ink">
                  {theme === 'dark' ? 'dark' : 'light'}
                </span>{' '}
                investigative theme.
              </p>
            </div>
            <AppearanceToggle />
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader
            title="Backend connection"
            description="Live reachability of the CNAS FastAPI service."
            actions={
              <Button
                size="sm"
                onClick={recheck}
                icon={<RefreshCw size={13} strokeWidth={1.75} />}
              >
                Re-check
              </Button>
            }
          />
          <PanelBody className="divide-y divide-line p-0">
            <Row label="Status">
              <StatusIndicator
                tone={TONE_BY_STATUS[status]}
                label={LABEL_BY_STATUS[status]}
                {...(latencyMs === null ? {} : { detail: `${latencyMs}ms` })}
              />
            </Row>
            <Row label="Base URL">
              <code className="font-mono text-2xs text-ink">
                {API_BASE_URL}
              </code>
            </Row>
            <Row label="Resolved from">
              <code className="font-mono text-2xs text-ink-muted">
                {baseUrlSource}
              </code>
            </Row>
            <Row label="Request timeout">
              <span className="font-mono tabular-nums">
                {REQUEST_TIMEOUT_MS / 1000}s
              </span>
            </Row>
            <Row label="Last checked">
              {checkedAt ? checkedAt.toLocaleTimeString() : '—'}
            </Row>
            {message ? (
              <Row label="Last error">
                <span className="text-signal-critical">{message}</span>
              </Row>
            ) : null}
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader
            title="Risk score bands"
            description="Thresholds applied by the backend rule engine. Scores prioritise investigative attention only."
          />
          <PanelBody className="divide-y divide-line p-0">
            {RISK_LEVELS.map((level) => (
              <Row key={level} label={`${level} band`}>
                <span className="inline-flex items-center gap-2">
                  <span className="font-mono text-2xs text-ink-muted tabular-nums">
                    {RISK_LEVEL_RANGE[level].min}–{RISK_LEVEL_RANGE[level].max}
                  </span>
                  <RiskBadge level={level} />
                </span>
              </Row>
            ))}
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader
            title="Build environment"
            description="Reported by Vite for the running bundle."
          />
          <PanelBody className="divide-y divide-line p-0">
            <Row label="Mode">
              <code className="font-mono text-2xs">
                {import.meta.env.MODE}
              </code>
            </Row>
            <Row label="Development build">
              {import.meta.env.DEV ? 'Yes' : 'No'}
            </Row>
          </PanelBody>
        </Panel>
      </div>
    </div>
  )
}
