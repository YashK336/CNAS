import { Check } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

export interface CheckboxProps {
  label: ReactNode
  checked: boolean
  onChange: (checked: boolean) => void
  /** Right-aligned secondary text, typically a count. */
  detail?: ReactNode
  /** Small colour swatch shown before the label. */
  swatchClass?: string
  disabled?: boolean
}

/** Compact filter row. The native input keeps keyboard and screen readers. */
export function Checkbox({
  label,
  checked,
  onChange,
  detail,
  swatchClass,
  disabled = false,
}: CheckboxProps) {
  return (
    <label
      className={cn(
        'flex items-center gap-2 rounded-sm px-1.5 py-1 text-xs',
        disabled
          ? 'cursor-not-allowed opacity-45'
          : 'cursor-pointer hover:bg-surface-hover',
      )}
    >
      <span className="relative inline-flex h-3.5 w-3.5 shrink-0">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
          className="h-3.5 w-3.5 cursor-pointer appearance-none rounded-sm border border-line-strong bg-surface-raised checked:border-accent/70 checked:bg-accent/20 disabled:cursor-not-allowed"
        />
        {checked ? (
          <Check
            size={11}
            strokeWidth={3}
            className="pointer-events-none absolute top-[1px] left-[1px] text-accent"
          />
        ) : null}
      </span>

      {swatchClass ? (
        <span
          aria-hidden
          className={cn('h-2 w-2 shrink-0 rounded-full', swatchClass)}
        />
      ) : null}

      <span className="min-w-0 flex-1 truncate text-ink">{label}</span>

      {detail ? (
        <span className="shrink-0 font-mono text-2xs text-ink-faint tabular-nums">
          {detail}
        </span>
      ) : null}
    </label>
  )
}
