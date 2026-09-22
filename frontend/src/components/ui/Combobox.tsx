import { Search, X } from 'lucide-react'
import { useId, useMemo, useRef, useState } from 'react'
import type { FocusEvent, KeyboardEvent } from 'react'

import { cn } from '@/lib/cn'

export interface ComboboxOption {
  id: string
  label: string
  detail?: string
  swatchClass?: string
}

export interface ComboboxProps {
  /** Visible field label. */
  label: string
  placeholder?: string
  /** Returns matches for the typed text. */
  search: (query: string) => ComboboxOption[]
  selected: ComboboxOption | null
  onSelect: (option: ComboboxOption) => void
  onClear?: () => void
  emptyMessage?: string
  disabled?: boolean
}

/**
 * Type-to-filter entity picker.
 *
 * The result list renders in normal flow rather than as an overlay, so it can
 * never be clipped by the scrolling panel it lives in.
 */
export function Combobox({
  label,
  placeholder = 'Search…',
  search,
  selected,
  onSelect,
  onClear,
  emptyMessage = 'No matches',
  disabled = false,
}: ComboboxProps) {
  const listId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const matches = useMemo(
    () => (open ? search(query) : []),
    [open, query, search],
  )

  const active = matches[Math.min(activeIndex, matches.length - 1)] ?? null

  const commit = (option: ComboboxOption) => {
    onSelect(option)
    setQuery('')
    setOpen(false)
    setActiveIndex(0)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      if (!open) {
        setOpen(true)
        return
      }
      setActiveIndex((current) => {
        if (matches.length === 0) return 0
        const next = event.key === 'ArrowDown' ? current + 1 : current - 1
        return (next + matches.length) % matches.length
      })
      return
    }

    if (event.key === 'Enter') {
      if (open && active) {
        event.preventDefault()
        commit(active)
      }
      return
    }

    if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  const onBlurCapture = (event: FocusEvent<HTMLDivElement>) => {
    if (event.currentTarget.contains(event.relatedTarget)) return
    setOpen(false)
  }

  return (
    <div onBlur={onBlurCapture}>
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          {label}
        </span>
        {selected && onClear ? (
          <button
            type="button"
            onClick={() => {
              onClear()
              setQuery('')
            }}
            className="inline-flex items-center gap-1 text-2xs text-ink-faint hover:text-ink"
          >
            <X size={10} strokeWidth={2} />
            Clear
          </button>
        ) : null}
      </div>

      {selected ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            setOpen(true)
            inputRef.current?.focus()
          }}
          className="flex w-full items-center gap-2 rounded-sm border border-accent/45 bg-accent-muted px-2 py-1.5 text-left hover:border-accent/70 disabled:pointer-events-none disabled:opacity-45"
        >
          {selected.swatchClass ? (
            <span
              aria-hidden
              className={cn(
                'h-2 w-2 shrink-0 rounded-full',
                selected.swatchClass,
              )}
            />
          ) : null}
          <span className="min-w-0 flex-1 truncate text-xs text-ink">
            {selected.label}
          </span>
          <span className="shrink-0 font-mono text-2xs text-accent">
            {selected.id}
          </span>
        </button>
      ) : null}

      <div className={cn('relative', selected && 'mt-1.5')}>
        <Search
          size={12}
          strokeWidth={1.75}
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-2 -translate-y-1/2 text-ink-faint"
        />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          autoComplete="off"
          spellCheck={false}
          disabled={disabled}
          value={query}
          placeholder={selected ? 'Replace…' : placeholder}
          onChange={(event) => {
            setQuery(event.target.value)
            setOpen(true)
            setActiveIndex(0)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          className="h-7 w-full rounded-sm border border-line-strong bg-surface-raised pr-2 pl-7 text-xs text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none disabled:opacity-45"
        />
      </div>

      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="mt-1 max-h-52 overflow-y-auto rounded-sm border border-line bg-surface-raised py-0.5"
        >
          {matches.length === 0 ? (
            <li className="px-2 py-1.5 text-2xs text-ink-faint">
              {emptyMessage}
            </li>
          ) : (
            matches.map((option, index) => (
              <li key={option.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={option.id === active?.id}
                  // Prevents the input blur that would close the list first.
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => commit(option)}
                  className={cn(
                    'flex w-full items-center gap-2 px-2 py-1 text-left',
                    option.id === active?.id
                      ? 'bg-surface-active'
                      : 'hover:bg-surface-hover',
                  )}
                >
                  {option.swatchClass ? (
                    <span
                      aria-hidden
                      className={cn(
                        'h-1.5 w-1.5 shrink-0 rounded-full',
                        option.swatchClass,
                      )}
                    />
                  ) : null}
                  <span className="min-w-0 flex-1 truncate text-xs text-ink">
                    {option.label}
                  </span>
                  <span className="shrink-0 font-mono text-2xs text-ink-faint">
                    {option.detail ?? option.id}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  )
}
