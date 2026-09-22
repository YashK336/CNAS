import { Network, RefreshCw, RotateCcw, TriangleAlert } from 'lucide-react'
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import {
  CommunityHighlightPanel,
  ConnectionTracePanel,
  EntityInspector,
  GraphFilterPanel,
  GraphSearchPanel,
  GraphSummaryStrip,
  GraphTemporalFilterPanel,
  LazyNetworkGraphCanvas,
  PathInspector,
  toApiDatetime,
} from '@/components/network'
import { SaveInvestigationPanel, InvestigationWorkspaceBanner } from '@/components/investigations'
import {
  Button,
  EmptyState,
  Panel,
  PanelBody,
  SectionHeader,
  Skeleton,
} from '@/components/ui'
import { useNetworkExplorerWorkspace } from '@/context/NetworkExplorerContext'
import {
  applySavedInvestigation,
  toDatetimeLocalValue,
} from '@/lib/investigations'
import {
  buildEntityOptions,
  buildGraphView,
  computeExplorationNodeIds,
  computeLayout,
  computeVisibleEdges,
  computeVisibleNodeIds,
  resolveActivePath,
} from '@/lib/graph'
import { resolveNeo4jPath } from '@/lib/neo4jGraph'
import {
  fetchConnection,
  fetchNeo4jPersonPath,
  getInvestigation,
  isAbortError,
  isForbidden,
  isUnauthorized,
  toErrorMessage,
} from '@/services'
import type {
  AggregatedEdge,
  EntityType,
  GraphFilters,
  GraphView,
  Point,
  TraceState,
} from '@/types'
import { ENTITY_TYPES } from '@/types'

const NO_IDS: string[] = []
const NO_ID_SET: ReadonlySet<string> = new Set<string>()
const NO_EDGES: AggregatedEdge[] = []
const NO_POSITIONS: ReadonlyMap<string, Point> = new Map()
const EMPTY_VIEW: GraphView = { nodes: [], edges: [] }
const IDLE_TRACE: TraceState = { status: 'idle' }

function WorkspaceLoading({ label }: { label: string }) {
  return (
    <EmptyState
      className="h-full"
      icon={
        <RefreshCw size={16} strokeWidth={1.75} className="animate-spin" />
      }
      title={label}
      description="The backend rebuilds the graph on request, so the first load takes a moment."
    />
  )
}

function ControlSkeleton() {
  return (
    <Panel>
      <PanelBody className="space-y-2 p-2.5">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-full" />
      </PanelBody>
    </Panel>
  )
}

export function NetworkExplorerPage() {
  const {
    graph,
    summary,
    communities,
    index,
    reload,
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
  } = useNetworkExplorerWorkspace()

  const temporalWindowActive =
    appliedWindow.fromDatetime !== null || appliedWindow.toDatetime !== null

  useEffect(() => () => traceAbortRef.current?.abort(), [traceAbortRef])

  const activeRelationships = useMemo<ReadonlySet<string>>(
    () => relationshipSelection ?? new Set(index?.relationshipTypes ?? []),
    [relationshipSelection, index],
  )

  const filters = useMemo<GraphFilters>(
    () => ({ entityTypes, relationships: activeRelationships }),
    [entityTypes, activeRelationships],
  )

  const handleEntityTypes = useCallback(
    (types: ReadonlySet<EntityType>) => {
      setEntityTypes(types)
      requestViewport('fit')
    },
    [requestViewport, setEntityTypes],
  )

  const handleRelationships = useCallback(
    (relationships: ReadonlySet<string>) => {
      setRelationshipSelection(relationships)
      requestViewport('fit')
    },
    [requestViewport, setRelationshipSelection],
  )

  const resetFilters = useCallback(() => {
    setEntityTypes(new Set(ENTITY_TYPES))
    setRelationshipSelection(null)
    setSelectedCommunity(null)
    requestViewport('fit')
  }, [requestViewport, setEntityTypes, setRelationshipSelection, setSelectedCommunity])

  const applyTemporalWindow = useCallback(() => {
    setAppliedWindow({
      fromDatetime: toApiDatetime(draftFrom),
      toDatetime: toApiDatetime(draftTo),
    })
  }, [draftFrom, draftTo, setAppliedWindow])

  const clearTemporalWindow = useCallback(() => {
    setDraftFrom('')
    setDraftTo('')
    setAppliedWindow({ fromDatetime: null, toDatetime: null })
  }, [setAppliedWindow, setDraftFrom, setDraftTo])

  const filtersDirty = useMemo(() => {
    if (entityTypes.size !== ENTITY_TYPES.length) return true
    if (selectedCommunity !== null) return true
    if (relationshipSelection && index) {
      return relationshipSelection.size !== index.relationshipTypes.length
    }
    return false
  }, [entityTypes, selectedCommunity, relationshipSelection, index])

  const [exploreFocusId, setExploreFocusId] = useState<string | null>(null)
  const [exploreHops, setExploreHops] = useState<1 | 2 | 3>(1)

  const selectedNodeId = selection?.kind === 'node' ? selection.id : null
  const exploreFocusIdEffective =
    selectedNodeId ?? (selection?.kind === 'edge' ? exploreFocusId : null)
  const exploreHopsEffective: 1 | 2 | 3 =
    selectedNodeId !== null && selectedNodeId !== exploreFocusId
      ? 1
      : exploreHops

  useEffect(() => {
    if (selectedNodeId !== null) {
      if (exploreFocusId !== selectedNodeId) {
        setExploreFocusId(selectedNodeId)
        setExploreHops(1)
      }
      return
    }

    if (selection === null && exploreFocusId !== null) {
      setExploreFocusId(null)
      setExploreHops(1)
    }
  }, [exploreFocusId, selectedNodeId, selection])

  const selectNode = useCallback(
    (entityId: string) => {
      setSelection({ kind: 'node', id: entityId })
      requestViewport('fit')
    },
    [requestViewport, setSelection],
  )

  const selectEdge = useCallback(
    (edgeId: string) => setSelection({ kind: 'edge', id: edgeId }),
    [setSelection],
  )

  const clearSelection = useCallback(() => {
    setSelection(null)
    requestViewport('fit')
  }, [requestViewport, setSelection])

  const focusEntity = useCallback(
    (entityId: string) => {
      setSelection({ kind: 'node', id: entityId })
      requestViewport('fit')
    },
    [requestViewport, setSelection],
  )

  const handleExploreHops = useCallback(
    (hops: 1 | 2 | 3) => {
      setExploreHops(hops)
      requestViewport('fit')
    },
    [requestViewport],
  )

  const resetOverview = useCallback(() => {
    setSelection(null)
    setExploreFocusId(null)
    setExploreHops(1)
    requestViewport('fit')
  }, [requestViewport, setSelection])

  const focusParam = useSearchParams()[0].get('focus')
  const investigationParam = useSearchParams()[0].get('investigation')
  const focusedRef = useRef<string | null>(null)
  const restoredInvestigationRef = useRef<string | null>(null)

  useEffect(() => {
    if (!index || focusParam === null) return
    if (focusedRef.current === focusParam) return
    if (!index.nodesById.has(focusParam)) return

    focusedRef.current = focusParam
    focusEntity(focusParam)
  }, [index, focusParam, focusEntity])

  useEffect(() => {
    if (!investigationParam) {
      return
    }
    if (restoredInvestigationRef.current === investigationParam) return

    const controller = new AbortController()
    setRestoreError(null)

    void getInvestigation(investigationParam, { signal: controller.signal })
      .then((investigation) => {
        if (controller.signal.aborted) return

        restoredInvestigationRef.current = investigationParam
        setActiveInvestigation(investigation)
        const snapshot = applySavedInvestigation(investigation)

        setSourceId(snapshot.traceSourceId)
        setTargetId(snapshot.traceTargetId)
        setDraftFrom(toDatetimeLocalValue(snapshot.fromDatetime))
        setDraftTo(toDatetimeLocalValue(snapshot.toDatetime))
        setAppliedWindow({
          fromDatetime: snapshot.fromDatetime,
          toDatetime: snapshot.toDatetime,
        })

        if (snapshot.selectedNodeId) {
          setSelection({ kind: 'node', id: snapshot.selectedNodeId })
          if (index?.nodesById.has(snapshot.selectedNodeId)) {
            requestViewport('fit')
          }
        } else {
          setSelection(null)
        }

        setTrace(IDLE_TRACE)
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) return
        setActiveInvestigation(null)
        if (isUnauthorized(error)) {
          setRestoreError('Your session expired while restoring this investigation.')
        } else if (isForbidden(error)) {
          setRestoreError('This investigation is outside your jurisdiction.')
        } else {
          setRestoreError(toErrorMessage(error))
        }
      })

    return () => controller.abort()
  }, [
    investigationParam,
    index,
    requestViewport,
    setActiveInvestigation,
    setAppliedWindow,
    setDraftFrom,
    setDraftTo,
    setRestoreError,
    setSelection,
    setSourceId,
    setTargetId,
    setTrace,
  ])

  const communityMembers = useMemo<ReadonlySet<string>>(
    () =>
      new Set(
        selectedCommunity?.members.map((member) => member.entity_id) ?? [],
      ),
    [selectedCommunity],
  )

  const handleCommunitySelect = useCallback(
    (community: typeof selectedCommunity) => {
      if (
        community === null ||
        selectedCommunity?.community_id === community.community_id
      ) {
        setSelectedCommunity(null)
        requestViewport('fit')
        return
      }

      setSelectedCommunity(community)
      const members = community.members.map((member) => member.entity_id)
      requestViewport(members.length > 0 ? 'nodes' : 'fit', members)
    },
    [requestViewport, selectedCommunity, setSelectedCommunity],
  )

  const runTrace = useCallback(() => {
    if (!index || sourceId === null || targetId === null) return

    traceAbortRef.current?.abort()
    const controller = new AbortController()
    traceAbortRef.current = controller
    setTrace({ status: 'loading' })

    const traceRequest = temporalWindowActive
      ? fetchNeo4jPersonPath(sourceId, targetId, appliedWindow, 6, {
          signal: controller.signal,
        }).then((result) => {
          if (controller.signal.aborted) return

          if (!result.found) {
            setTrace({ status: 'not-found', message: result.message })
            return
          }

          const path = resolveNeo4jPath(result, index)
          setTrace({ status: 'found', path })
          requestViewport('nodes', path.nodeIds)
        })
      : fetchConnection(sourceId, targetId, { signal: controller.signal }).then(
          (result) => {
            if (controller.signal.aborted) return

            if (!result.found) {
              setTrace({ status: 'not-found', message: result.message })
              return
            }

            const path = resolveActivePath(result, index)
            setTrace({ status: 'found', path })
            requestViewport('nodes', path.nodeIds)
          },
        )

    void traceRequest.catch((error: unknown) => {
      if (isAbortError(error)) return
      setTrace({ status: 'error', message: toErrorMessage(error) })
    })
  }, [
    index,
    sourceId,
    targetId,
    requestViewport,
    temporalWindowActive,
    appliedWindow,
    setTrace,
    traceAbortRef,
  ])

  const clearPath = useCallback(() => {
    traceAbortRef.current?.abort()
    setTrace(IDLE_TRACE)
    requestViewport('fit')
  }, [requestViewport, setTrace, traceAbortRef])

  const activePath = trace.status === 'found' ? trace.path : null

  const focusPath = useCallback(() => {
    if (activePath) requestViewport('nodes', activePath.nodeIds)
  }, [activePath, requestViewport])

  const pathNodeIds = activePath?.nodeIds ?? NO_IDS
  const pathEdgeIds = activePath?.edgeIds ?? NO_ID_SET

  const filteredNodeIds = useMemo(
    () =>
      index ? computeVisibleNodeIds(index, filters, pathNodeIds) : NO_ID_SET,
    [index, filters, pathNodeIds],
  )

  const visibleNodeIds = useMemo(
    () =>
      index
        ? computeExplorationNodeIds(index, {
            filteredIds: filteredNodeIds,
            selectedNodeId: exploreFocusIdEffective,
            hopDepth: exploreHopsEffective,
            pathNodeIds,
            communityMembers,
          })
        : NO_ID_SET,
    [
      index,
      filteredNodeIds,
      exploreFocusIdEffective,
      exploreHopsEffective,
      pathNodeIds,
      communityMembers,
    ],
  )

  const visibleEdges = useMemo(
    () =>
      index
        ? computeVisibleEdges(index, filters, visibleNodeIds, pathEdgeIds)
        : NO_EDGES,
    [index, filters, visibleNodeIds, pathEdgeIds],
  )

  const positions = useMemo(
    () =>
      index
        ? computeLayout(index, visibleNodeIds, {
            focusNodeId: exploreFocusIdEffective,
          })
        : NO_POSITIONS,
    [index, visibleNodeIds, exploreFocusIdEffective],
  )

  const view = useMemo<GraphView>(
    () =>
      index
        ? buildGraphView({
            index,
            visibleNodeIds,
            visibleEdges,
            positions,
            selection,
            communityMembers,
            path: activePath,
            exploreFocusId: exploreFocusIdEffective,
            explorationHops: exploreHopsEffective,
          })
        : EMPTY_VIEW,
    [
      index,
      visibleNodeIds,
      visibleEdges,
      positions,
      selection,
      communityMembers,
      activePath,
      exploreFocusIdEffective,
      exploreHopsEffective,
    ],
  )

  const entityOptions = useMemo(
    () => (index ? buildEntityOptions(index.nodes) : []),
    [index],
  )

  const graphFailed = graph.error !== null && index === null

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Graph analysis"
        title="Network Explorer"
        description="Interactive investigation graph across people, vehicles, cases, surveillance and their relationships."
        actions={
          <Button
            size="sm"
            onClick={reload}
            disabled={graph.isLoading}
            icon={
              <RefreshCw
                size={13}
                strokeWidth={1.75}
                className={graph.isLoading ? 'animate-spin' : undefined}
              />
            }
          >
            {graph.isLoading ? 'Loading' : 'Reload graph'}
          </Button>
        }
      />

      <InvestigationWorkspaceBanner
        investigation={activeInvestigation}
        restoreError={restoreError}
      />

      <div className="flex flex-col gap-4 xl:h-[calc(100vh-13.5rem)] xl:min-h-[600px] xl:flex-row">
        <aside className="order-2 flex w-full shrink-0 flex-col gap-3 xl:order-1 xl:w-[266px] xl:overflow-y-auto xl:pr-1">
          <GraphSummaryStrip
            summary={summary.data}
            error={summary.error}
            onRetry={summary.refetch}
            visibleNodes={view.nodes.length}
            visibleLinks={view.edges.length}
            totalDrawnLinks={index?.edges.length ?? 0}
            totalNodes={index?.nodes.length ?? 0}
          />

          {index ? (
            <>
              <GraphSearchPanel
                options={entityOptions}
                onSelect={focusEntity}
              />

              <GraphFilterPanel
                index={index}
                filters={filters}
                onEntityTypesChange={handleEntityTypes}
                onRelationshipsChange={handleRelationships}
              />
            </>
          ) : (
            <ControlSkeleton />
          )}

          <CommunityHighlightPanel
            communities={communities.data}
            isLoading={communities.isLoading}
            error={communities.error}
            onRetry={communities.refetch}
            selectedCommunityId={selectedCommunity?.community_id ?? null}
            onSelect={handleCommunitySelect}
          />

          {index ? (
            <ConnectionTracePanel
              options={entityOptions}
              sourceId={sourceId}
              targetId={targetId}
              onSourceChange={setSourceId}
              onTargetChange={setTargetId}
              onTrace={runTrace}
              isTracing={trace.status === 'loading'}
            />
          ) : null}

          <GraphTemporalFilterPanel
            draftFrom={draftFrom}
            draftTo={draftTo}
            appliedWindow={appliedWindow}
            onDraftFromChange={setDraftFrom}
            onDraftToChange={setDraftTo}
            onApply={applyTemporalWindow}
            onClear={clearTemporalWindow}
          />

          <SaveInvestigationPanel
            sourceId={sourceId}
            targetId={targetId}
            selectionNodeId={
              selection?.kind === 'node' ? selection.id : null
            }
            fromDatetime={appliedWindow.fromDatetime}
            toDatetime={appliedWindow.toDatetime}
            onSaved={setActiveInvestigation}
          />
        </aside>

        <Panel className="relative order-1 h-[560px] overflow-hidden xl:order-2 xl:h-auto xl:min-w-0 xl:flex-1">
          <div className="absolute inset-0">
            {graphFailed ? (
              <EmptyState
                className="h-full"
                icon={<TriangleAlert size={16} strokeWidth={1.75} />}
                title="Unable to load network graph."
                description={graph.error ?? undefined}
                actions={
                  <Button
                    onClick={graph.refetch}
                    icon={<RefreshCw size={13} strokeWidth={1.75} />}
                  >
                    Retry
                  </Button>
                }
              />
            ) : !index ? (
              <WorkspaceLoading label="Loading network graph…" />
            ) : view.nodes.length === 0 ? (
              <EmptyState
                className="h-full"
                icon={<Network size={16} strokeWidth={1.75} />}
                title="No entities match the current filters."
                description="Every entity type is hidden, so there is nothing to draw."
                actions={
                  <Button
                    onClick={resetFilters}
                    icon={<RotateCcw size={13} strokeWidth={1.75} />}
                  >
                    Reset filters
                  </Button>
                }
              />
            ) : (
              <Suspense
                fallback={<WorkspaceLoading label="Preparing graph canvas…" />}
              >
                <LazyNetworkGraphCanvas
                  view={view}
                  viewport={viewport}
                  onSelectNode={selectNode}
                  onSelectEdge={selectEdge}
                  onClearSelection={clearSelection}
                  onClearPath={clearPath}
                  onResetFilters={resetFilters}
                  canClearSelection={selection !== null}
                  canClearPath={trace.status !== 'idle'}
                  canResetFilters={filtersDirty}
                  exploreHops={exploreHopsEffective}
                  exploreActive={exploreFocusIdEffective !== null}
                  onExploreHopsChange={handleExploreHops}
                  onResetOverview={resetOverview}
                />
              </Suspense>
            )}
          </div>
        </Panel>

        <aside className="order-3 flex w-full shrink-0 flex-col gap-3 xl:w-[320px] xl:overflow-y-auto xl:pl-1">
          {index ? (
            <>
              <PathInspector
                state={trace}
                index={index}
                onClear={clearPath}
                onFocus={focusPath}
                onRetry={runTrace}
                onSelectNode={focusEntity}
              />

              <EntityInspector
                index={index}
                selection={selection}
                onSetTraceSource={setSourceId}
                onSetTraceTarget={setTargetId}
              />
            </>
          ) : (
            <ControlSkeleton />
          )}
        </aside>
      </div>
    </div>
  )
}
