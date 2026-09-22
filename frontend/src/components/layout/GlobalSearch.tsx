import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'

import { personsResource } from '@/services/cache'
import type { Person } from '@/types'

interface SearchOption {
  id: string
  label: string
  meta: string
}

function buildOptions(persons: Person[]): SearchOption[] {
  return persons.map((person) => ({
    id: person.person_id,
    label: person.name,
    meta: `${person.person_id} · ${person.home_city ?? 'Unknown city'}`,
  }))
}

/**
 * Quick entity lookup against the existing persons roster.
 * Navigates to person detail or filtered people list.
 */
export function GlobalSearch() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [options, setOptions] = useState<SearchOption[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    setIsLoading(true)
    void personsResource
      .load()
      .then((persons) => {
        if (!active) return
        setOptions(buildOptions(persons))
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [])

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return options.slice(0, 8)
    return options
      .filter(
        (option) =>
          option.label.toLowerCase().includes(normalized) ||
          option.id.toLowerCase().includes(normalized) ||
          option.meta.toLowerCase().includes(normalized),
      )
      .slice(0, 8)
  }, [options, query])

  const handleSelect = (option: SearchOption) => {
    setQuery('')
    setIsOpen(false)
    navigate(`/people/${encodeURIComponent(option.id)}`)
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-lg">
      <div className="flex h-7 items-center gap-2 rounded-sm border border-line bg-surface px-2.5">
        <Search size={13} strokeWidth={1.75} className="shrink-0 text-ink-faint" />
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
          placeholder="Search people by name or ID"
          className="min-w-0 flex-1 bg-transparent text-xs text-ink placeholder:text-ink-faint focus:outline-none"
          aria-label="Search people"
        />
        <kbd className="hidden shrink-0 rounded-sm border border-line bg-surface-raised px-1.5 py-0.5 font-mono text-2xs text-ink-faint sm:inline-block">
          /
        </kbd>
      </div>

      {isOpen && (query.trim() !== '' || isLoading) ? (
        <div className="absolute top-[calc(100%+4px)] z-40 w-full overflow-hidden rounded-sm border border-line-strong bg-surface-raised shadow-[0_12px_32px_rgba(0,0,0,0.35)]">
          {isLoading ? (
            <p className="px-3 py-2 text-xs text-ink-muted">Loading roster…</p>
          ) : filtered.length === 0 ? (
            <p className="px-3 py-2 text-xs text-ink-muted">No matching people.</p>
          ) : (
            <ul className="max-h-64 overflow-y-auto py-1">
              {filtered.map((option) => (
                <li key={option.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(option)}
                    className="flex w-full flex-col items-start px-3 py-2 text-left hover:bg-surface-hover"
                  >
                    <span className="text-xs font-medium text-ink">{option.label}</span>
                    <span className="text-2xs text-ink-muted">{option.meta}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
