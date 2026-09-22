import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
  type ReactNode,
} from 'react'

import type { ViewportCommand } from '@/components/network'
import { useNetworkGraph } from '@/hooks/useNetworkGraph'
import type { NetworkGraphData } from '@/hooks/useNetworkGraph'
import type {
  Community,
  EntityType,
  GraphSelection,
  SavedInvestigation,
  TraceState,
} from '@/types'
import { ENTITY_TYPES } from '@/types'
import type { TemporalWindow } from '@/services'

const ALL_ENTITY_TYPES: ReadonlySet<EntityType> = new Set(ENTITY_TYPES)
const IDLE_TRACE: TraceState = { status: 'idle' }
const INITIAL_VIEWPORT: ViewportCommand = { token: 0, kind: 'fit', ids: [] }

export interface NetworkExplorerWorkspaceState {
  entityTypes: ReadonlySet<EntityType>
  setEntityTypes: (types: ReadonlySet<EntityType>) => void
  relationshipSelection: ReadonlySet<string> | null
  setRelationshipSelection: (selection: ReadonlySet<string> | null) => void
  selection: GraphSelection | null
  setSelection: (selection: GraphSelection | null) => void
  selectedCommunity: Community | null
  setSelectedCommunity: (community: Community | null) => void
  sourceId: string | null
  setSourceId: (entityId: string | null) => void
  targetId: string | null
  setTargetId: (entityId: string | null) => void
  trace: TraceState
  setTrace: (trace: TraceState) => void
  viewport: ViewportCommand
  setViewport: React.Dispatch<React.SetStateAction<ViewportCommand>>
  draftFrom: string
  setDraftFrom: (value: string) => void
  draftTo: string
  setDraftTo: (value: string) => void
  appliedWindow: TemporalWindow
  setAppliedWindow: (window: TemporalWindow) => void
  activeInvestigation: SavedInvestigation | null
  setActiveInvestigation: (investigation: SavedInvestigation | null) => void
  restoreError: string | null
  setRestoreError: (message: string | null) => void
  traceAbortRef: MutableRefObject<AbortController | null>
  requestViewport: (kind: ViewportCommand['kind'], ids?: string[]) => void
}

export type NetworkExplorerContextValue = NetworkExplorerWorkspaceState &
  NetworkGraphData

const NetworkExplorerContext = createContext<NetworkExplorerContextValue | null>(
  null,
)

export function NetworkExplorerProvider({ children }: { children: ReactNode }) {
  const networkData = useNetworkGraph()

  const [entityTypes, setEntityTypes] =
    useState<ReadonlySet<EntityType>>(ALL_ENTITY_TYPES)
  const [relationshipSelection, setRelationshipSelection] =
    useState<ReadonlySet<string> | null>(null)
  const [selection, setSelection] = useState<GraphSelection | null>(null)
  const [selectedCommunity, setSelectedCommunity] = useState<Community | null>(
    null,
  )
  const [sourceId, setSourceId] = useState<string | null>(null)
  const [targetId, setTargetId] = useState<string | null>(null)
  const [trace, setTrace] = useState<TraceState>(IDLE_TRACE)
  const [viewport, setViewport] = useState<ViewportCommand>(INITIAL_VIEWPORT)
  const [draftFrom, setDraftFrom] = useState('')
  const [draftTo, setDraftTo] = useState('')
  const [appliedWindow, setAppliedWindow] = useState<TemporalWindow>({
    fromDatetime: null,
    toDatetime: null,
  })
  const [activeInvestigation, setActiveInvestigation] =
    useState<SavedInvestigation | null>(null)
  const [restoreError, setRestoreError] = useState<string | null>(null)

  const traceAbortRef = useRef<AbortController | null>(null)

  const requestViewport = useCallback(
    (kind: ViewportCommand['kind'], ids: string[] = []) => {
      setViewport((current) => ({ token: current.token + 1, kind, ids }))
    },
    [],
  )

  const value = useMemo<NetworkExplorerContextValue>(
    () => ({
      ...networkData,
      entityTypes,
      setEntityTypes,
      relationshipSelection,
      setRelationshipSelection,
      selection,
      setSelection,
      selectedCommunity,
      setSelectedCommunity,
      sourceId,
      setSourceId,
      targetId,
      setTargetId,
      trace,
      setTrace,
      viewport,
      setViewport,
      draftFrom,
      setDraftFrom,
      draftTo,
      setDraftTo,
      appliedWindow,
      setAppliedWindow,
      activeInvestigation,
      setActiveInvestigation,
      restoreError,
      setRestoreError,
      traceAbortRef,
      requestViewport,
    }),
    [
      networkData,
      entityTypes,
      relationshipSelection,
      selection,
      selectedCommunity,
      sourceId,
      targetId,
      trace,
      viewport,
      draftFrom,
      draftTo,
      appliedWindow,
      activeInvestigation,
      restoreError,
      requestViewport,
    ],
  )

  return (
    <NetworkExplorerContext.Provider value={value}>
      {children}
    </NetworkExplorerContext.Provider>
  )
}

export function useNetworkExplorerWorkspace(): NetworkExplorerContextValue {
  const context = useContext(NetworkExplorerContext)
  if (!context) {
    throw new Error(
      'useNetworkExplorerWorkspace must be used within NetworkExplorerProvider',
    )
  }
  return context
}
