import type { Theme } from './theme'

/**
 * SVG and canvas surfaces (Recharts, React Flow markers, the graph minimap)
 * need concrete colours rather than CSS variables. Dark values mirror the
 * default tokens in `src/index.css`; light values follow the light theme
 * overrides. Keep both in sync when tokens change.
 */
export const CHART_COLORS = {
  accent: '#4b8df8',
  axis: '#6a727d',
  label: '#98a1ac',
  cursor: 'rgba(255, 255, 255, 0.035)',
} as const

const LIGHT_CHART_COLORS = {
  accent: '#2f74e0',
  axis: '#6a7584',
  label: '#4b5666',
  cursor: 'rgba(27, 36, 48, 0.06)',
} as const

export function chartColorsFor(theme: Theme) {
  return theme === 'light' ? LIGHT_CHART_COLORS : CHART_COLORS
}

export const GRAPH_SURFACE = {
  dark: {
    dot: '#1b2028',
    minimapMask: 'rgba(8, 9, 11, 0.74)',
  },
  light: {
    dot: '#c5ced9',
    minimapMask: 'rgba(230, 235, 242, 0.74)',
  },
} as const

export function graphSurfaceFor(theme: Theme) {
  return GRAPH_SURFACE[theme]
}

export const CHART_FONT_SIZE = 11

/** Entity colours matching `ENTITY_PRESENTATION` in `src/lib/entities.ts`. */
export const ENTITY_HEX = {
  person: '#4b8df8',
  vehicle: '#6a727d',
  crime_event: '#d24f4f',
  surveillance_event: '#c3a02f',
} as const
