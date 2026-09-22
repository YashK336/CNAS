import { Search, X } from 'lucide-react'
import { useId } from 'react'

import { cn } from '@/lib/cn'

export interface SearchFieldProps {
  /** Accessible label; rendered only for screen readers. */
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  /** Small hint rendered inside the field's trailing edge, e.g. a match count. */
  hint?: string | undefined
  className?: string
}

/** Single-line filter input with a clear affordance. */
export function SearchField({
  label,
  value,
  onChange,
  placeholder = 'Search…',
  hint,
  className,
}: SearchFieldProps) {
  const inputId = useId()

  return (
    <div className={cn('relative', className)}>
      <label htmlFor={inputId} className="sr-only">
        {label}
      </label>

      <Search
        size={13}
        strokeWidth={1.75}
        aria-hidden
        className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-ink-faint"
      />

      <input
        id={inputId}
        type="search"
        autoComplete="off"
        spellCheck={false}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Escape' && value !== '') {
            event.preventDefault()
            onChange('')
          }
        }}
        // The native search clear button is suppressed in favour of the button
        // below, which matches the rest of the control language.
        className={cn(
          'h-8 w-full rounded-sm border border-line-strong bg-surface-raised pl-8 text-xs text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none [&::-webkit-search-cancel-button]:hidden',
          hint ? 'pr-20' : 'pr-9',
        )}
      />

      <div className="pointer-events-none absolute top-1/2 right-2 flex -translate-y-1/2 items-center gap-1.5">
        {hint ? (
          <span className="font-mono text-2xs text-ink-faint">{hint}</span>
        ) : null}
        {value === '' ? null : (
          <button
            type="button"
            onClick={() => onChange('')}
            aria-label="Clear search"
            className="pointer-events-auto inline-flex h-5 w-5 items-center justify-center rounded-sm text-ink-faint hover:bg-surface-hover hover:text-ink"
          >
            <X size={12} strokeWidth={2} />
          </button>
        )}
      </div>
    </div>
  )
}
