import { Moon, Sun } from 'lucide-react'
import type { KeyboardEvent } from 'react'

import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/cn'
import type { Theme } from '@/lib/theme'

const OPTIONS: { value: Theme; label: string; icon: typeof Moon }[] = [
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'light', label: 'Light', icon: Sun },
]

export function AppearanceToggle() {
  const { theme, setTheme } = useTheme()

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
    event.preventDefault()
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <div
      role="radiogroup"
      aria-label="Color theme"
      onKeyDown={handleKeyDown}
      className="inline-flex rounded-lg border border-line-strong bg-canvas p-1"
    >
      {OPTIONS.map(({ value, label, icon: Icon }) => {
        const selected = theme === value
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-label={`${label} theme`}
            onClick={() => setTheme(value)}
            className={cn(
              'inline-flex h-9 items-center gap-2 rounded-md px-3.5 text-xs font-semibold transition-[background-color,color,box-shadow] duration-150',
              selected
                ? 'bg-surface-raised text-ink shadow-sm'
                : 'text-ink-muted hover:text-ink',
            )}
          >
            <Icon size={14} strokeWidth={1.75} />
            {label}
          </button>
        )
      })}
    </div>
  )
}
