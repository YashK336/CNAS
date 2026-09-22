import { StatusIndicator } from '@/components/ui'
import type { StatusTone } from '@/components/ui'
import { useBackendStatus } from '@/hooks'
import type { BackendStatus } from '@/hooks'
import { API_BASE_URL } from '@/services'

const TONE_BY_STATUS: Record<BackendStatus, StatusTone> = {
  checking: 'pending',
  online: 'online',
  offline: 'offline',
}

const LABEL_BY_STATUS: Record<BackendStatus, string> = {
  checking: 'Linking',
  online: 'Online',
  offline: 'Offline',
}

/**
 * Live reachability of the FastAPI service. Click to re-probe immediately.
 */
export function BackendStatusChip() {
  const { status, latencyMs, checkedAt, message, recheck } = useBackendStatus()

  const detail = latencyMs === null ? null : `${latencyMs}ms`

  const titleLines = [
    `Backend: ${API_BASE_URL}`,
    checkedAt ? `Last checked: ${checkedAt.toLocaleTimeString()}` : null,
    message,
    'Click to re-check',
  ].filter((line): line is string => Boolean(line))

  return (
    <button
      type="button"
      onClick={recheck}
      title={titleLines.join('\n')}
      className="flex h-7 items-center gap-2 rounded-sm border border-line bg-surface px-2 transition-colors hover:border-line-strong hover:bg-surface-hover"
    >
      <span className="text-2xs font-medium tracking-wider text-ink-faint uppercase">
        API
      </span>
      <StatusIndicator
        tone={TONE_BY_STATUS[status]}
        label={LABEL_BY_STATUS[status]}
        {...(detail === null ? {} : { detail })}
      />
    </button>
  )
}
