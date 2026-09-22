export type ClassValue =
  | string
  | number
  | false
  | null
  | undefined
  | ClassValue[]

/**
 * Minimal conditional class joiner. Deliberately dependency free — variant
 * maps in this codebase never emit conflicting utilities, so full
 * `tailwind-merge` conflict resolution is not needed.
 */
export function cn(...values: ClassValue[]): string {
  const out: string[] = []

  for (const value of values) {
    if (!value && value !== 0) continue

    if (Array.isArray(value)) {
      const nested = cn(...value)
      if (nested) out.push(nested)
    } else {
      out.push(String(value))
    }
  }

  return out.join(' ')
}
