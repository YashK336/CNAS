import { lazy } from 'react'

export type {
  CommunitySizeChartProps,
  CommunitySizeDatum,
} from './CommunitySizeChart'

/** Recharts is code-split; render inside a `Suspense` boundary. */
export const LazyCommunitySizeChart = lazy(() =>
  import('./CommunitySizeChart').then((module) => ({
    default: module.CommunitySizeChart,
  })),
)
