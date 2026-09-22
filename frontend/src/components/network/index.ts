import { lazy } from 'react'

export { CommunityHighlightPanel } from './CommunityHighlightPanel'
export type { CommunityHighlightPanelProps } from './CommunityHighlightPanel'

export { ConnectionTracePanel } from './ConnectionTracePanel'
export type { ConnectionTracePanelProps } from './ConnectionTracePanel'

export { EntityInspector } from './EntityInspector'
export type { EntityInspectorProps } from './EntityInspector'

export { GraphFilterPanel } from './GraphFilterPanel'
export type { GraphFilterPanelProps } from './GraphFilterPanel'

export { GraphTemporalFilterPanel } from './GraphTemporalFilterPanel'
export type { GraphTemporalFilterPanelProps } from './GraphTemporalFilterPanel'
export { toApiDatetime, toDatetimeLocalValue } from './GraphTemporalFilterPanel'

export { GraphSearchPanel } from './GraphSearchPanel'
export type { GraphSearchPanelProps } from './GraphSearchPanel'

export { GraphSummaryStrip } from './GraphSummaryStrip'
export type { GraphSummaryStripProps } from './GraphSummaryStrip'

export { PathInspector } from './PathInspector'
export type { PathInspectorProps } from './PathInspector'

/** Type-only, so React Flow stays out of the initial bundle. */
export type {
  NetworkGraphCanvasProps,
  ViewportCommand,
} from './NetworkGraphCanvas'

/** React Flow is code-split; render inside a `Suspense` boundary. */
export const LazyNetworkGraphCanvas = lazy(() =>
  import('./NetworkGraphCanvas').then((module) => ({
    default: module.NetworkGraphCanvas,
  })),
)
