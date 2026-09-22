import { AlertTriangle, Check, CircleAlert, Info, X } from 'lucide-react'
import { useCallback, useState } from 'react'

import { cn } from '@/lib/cn'

export type ToastTone = 'success' | 'error' | 'warning' | 'info'

export interface ToastMessage {
  id: string
  tone: ToastTone
  title: string
  description?: string
}

const TONE_CLASS: Record<ToastTone, string> = {
  success: 'border-signal-low/45 bg-surface-raised text-ink',
  error: 'border-signal-critical/50 bg-surface-raised text-ink',
  warning: 'border-signal-medium/50 bg-surface-raised text-ink',
  info: 'border-accent/40 bg-surface-raised text-ink',
}

const TONE_ICON: Record<ToastTone, typeof Check> = {
  success: Check,
  error: CircleAlert,
  warning: AlertTriangle,
  info: Info,
}

const TONE_ICON_CLASS: Record<ToastTone, string> = {
  success: 'text-signal-low',
  error: 'text-signal-critical',
  warning: 'text-signal-medium',
  info: 'text-accent',
}

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[]
  onDismiss: (id: string) => void
}) {
  if (toasts.length === 0) return null

  return (
    <div
      className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((toast) => {
        const Icon = TONE_ICON[toast.tone]
        return (
          <div
            key={toast.id}
            className={cn(
              'pointer-events-auto flex gap-2 rounded-md border px-3 py-2.5 shadow-[0_12px_32px_rgba(0,0,0,0.28)]',
              TONE_CLASS[toast.tone],
            )}
            role="status"
          >
            <Icon
              size={14}
              strokeWidth={1.75}
              className={cn('mt-0.5 shrink-0', TONE_ICON_CLASS[toast.tone])}
            />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-ink">{toast.title}</p>
              {toast.description ? (
                <p className="mt-0.5 text-2xs leading-relaxed text-ink-muted">
                  {toast.description}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => onDismiss(toast.id)}
              className="shrink-0 text-ink-faint hover:text-ink"
              aria-label="Dismiss notification"
            >
              <X size={13} strokeWidth={1.75} />
            </button>
          </div>
        )
      })}
    </div>
  )
}

export function useToasts() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.filter((item) => item.id !== id))
  }, [])

  const push = useCallback(
    (tone: ToastTone, title: string, description?: string) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      const next: ToastMessage = { id, tone, title }
      if (description) next.description = description
      setToasts((current) => [...current.slice(-4), next])
      window.setTimeout(() => {
        setToasts((current) => current.filter((item) => item.id !== id))
      }, 7000)
    },
    [],
  )

  return { toasts, push, dismiss }
}
