const numberFormatter = new Intl.NumberFormat('en-IN')

const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const dateTimeFormatter = new Intl.DateTimeFormat('en-IN', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const dateFormatter = new Intl.DateTimeFormat('en-IN', {
  dateStyle: 'medium',
})

const timeFormatter = new Intl.DateTimeFormat('en-IN', {
  timeStyle: 'medium',
})

export const EMPTY_VALUE = '—'

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return EMPTY_VALUE
  }
  return numberFormatter.format(value)
}

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return EMPTY_VALUE
  }
  return currencyFormatter.format(value)
}

/** Renders a backend timestamp, falling back to the raw string if unparsable. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return EMPTY_VALUE
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : dateTimeFormatter.format(parsed)
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return EMPTY_VALUE
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : dateFormatter.format(parsed)
}

/** Seconds to a compact "1h 04m" / "2m 54s" / "48s". */
export function formatDuration(
  seconds: number | null | undefined,
): string {
  if (
    seconds === null ||
    seconds === undefined ||
    !Number.isFinite(seconds)
  ) {
    return EMPTY_VALUE
  }

  const total = Math.max(0, Math.round(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const rest = total % 60

  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')}m`
  if (minutes > 0) return `${minutes}m ${String(rest).padStart(2, '0')}s`
  return `${rest}s`
}

/** Clock time only, for "last loaded" style freshness labels. */
export function formatTime(value: Date | null | undefined): string {
  return value ? timeFormatter.format(value) : EMPTY_VALUE
}

export function formatText(value: string | null | undefined): string {
  const trimmed = value?.trim()
  return trimmed ? trimmed : EMPTY_VALUE
}

/** "Rajesh Kumar" -> "RK". Used for the compact identity chip. */
export function initials(value: string | null | undefined): string {
  if (!value) return '?'
  const parts = value.trim().split(/\s+/).slice(0, 2)
  const letters = parts.map((part) => part.charAt(0).toUpperCase()).join('')
  return letters || '?'
}
