import type { AnomalyLevel } from '@/types'

interface AnomalyLevelPresentation {
  label: string
  barClass: string
  textClass: string
}

export const ANOMALY_LEVEL_PRESENTATION: Record<
  AnomalyLevel,
  AnomalyLevelPresentation
> = {
  NORMAL: {
    label: 'Normal',
    barClass: 'bg-signal-low',
    textClass: 'text-signal-low',
  },
  ELEVATED: {
    label: 'Elevated',
    barClass: 'bg-signal-medium',
    textClass: 'text-signal-medium',
  },
  HIGH: {
    label: 'High',
    barClass: 'bg-signal-high',
    textClass: 'text-signal-high',
  },
  EXTREME: {
    label: 'Extreme',
    barClass: 'bg-signal-critical',
    textClass: 'text-signal-critical',
  },
}

export const ANOMALY_FEATURE_LABELS = {
  communication: 'Communication',
  financial: 'Financial',
  social: 'Social',
  surveillance: 'Surveillance',
} as const
