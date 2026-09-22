export type Theme = 'dark' | 'light'

export const THEME_STORAGE_KEY = 'cnas.theme'
export const DEFAULT_THEME: Theme = 'dark'

export function isTheme(value: string | null): value is Theme {
  return value === 'dark' || value === 'light'
}

export function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    if (isTheme(stored)) return stored
  } catch {
    // Private mode or blocked storage — stay on the dark default.
  }
  return DEFAULT_THEME
}

export function persistTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Preference stays in-memory for this session only.
  }
}

/** Writes theme onto <html> so CSS tokens and native form chrome stay in sync. */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement
  root.setAttribute('data-theme', theme)
  root.style.colorScheme = theme
  root.classList.toggle('dark', theme === 'dark')

  const meta = document.querySelector('meta[name="color-scheme"]')
  if (meta) {
    meta.setAttribute('content', theme)
  }
}
