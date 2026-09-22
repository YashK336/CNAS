import { CircleAlert, RefreshCw } from 'lucide-react'

import { Button } from './Button'
import { EmptyState } from './EmptyState'

export interface SectionErrorProps {
  message: string
  onRetry?: () => void
  /** Tighter padding for use inside small panels. */
  compact?: boolean
}

/**
 * Inline failure state for a single dashboard section, so one failed endpoint
 * never takes down the whole page.
 */
export function SectionError({
  message,
  onRetry,
  compact = false,
}: SectionErrorProps) {
  return (
    <EmptyState
      className={compact ? 'px-4 py-6' : 'px-6 py-10'}
      icon={<CircleAlert size={16} strokeWidth={1.75} />}
      title="Could not load this section"
      description={message}
      actions={
        onRetry ? (
          <Button
            size="sm"
            onClick={onRetry}
            icon={<RefreshCw size={13} strokeWidth={1.75} />}
          >
            Retry
          </Button>
        ) : null
      }
    />
  )
}
