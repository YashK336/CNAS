import type { RiskLevel } from '@/types'

interface RiskLevelPresentation {
  label: string
  /** Solid colour for meters, dots and chart series. */
  barClass: string
  textClass: string
}

/**
 * Single source of truth for risk colour. Badge treatments live in the shared
 * `Badge` tones, which map 1:1 to these levels.
 */
export const RISK_LEVEL_PRESENTATION: Record<RiskLevel, RiskLevelPresentation> =
  {
    LOW: {
      label: 'Low',
      barClass: 'bg-signal-low',
      textClass: 'text-signal-low',
    },
    MEDIUM: {
      label: 'Medium',
      barClass: 'bg-signal-medium',
      textClass: 'text-signal-medium',
    },
    HIGH: {
      label: 'High',
      barClass: 'bg-signal-high',
      textClass: 'text-signal-high',
    },
    CRITICAL: {
      label: 'Critical',
      barClass: 'bg-signal-critical',
      textClass: 'text-signal-critical',
    },
  }

/** Score bands, mirroring `_risk_level` in the backend analytics service. */
export const RISK_LEVEL_RANGE: Record<RiskLevel, { min: number; max: number }> =
  {
    LOW: { min: 0, max: 24 },
    MEDIUM: { min: 25, max: 49 },
    HIGH: { min: 50, max: 74 },
    CRITICAL: { min: 75, max: 100 },
  }

/**
 * The API already returns `risk_level`; this exists for locally derived scores
 * and keeps the thresholds defined in exactly one place.
 */
export function riskLevelFromScore(score: number): RiskLevel {
  if (score >= RISK_LEVEL_RANGE.CRITICAL.min) return 'CRITICAL'
  if (score >= RISK_LEVEL_RANGE.HIGH.min) return 'HIGH'
  if (score >= RISK_LEVEL_RANGE.MEDIUM.min) return 'MEDIUM'
  return 'LOW'
}

/** Human labels for the backend `signal_scores` keys. */
export const RISK_SIGNAL_LABELS = {
  network_influence: 'Network influence',
  fir_involvement: 'FIR involvement',
  financial_activity: 'Financial activity',
  communication_activity: 'Communication activity',
  social_activity: 'Social activity',
  surveillance_activity: 'Surveillance activity',
  network_bridge_role: 'Network bridge role',
  graph_propagation: 'Graph propagation',
} as const
