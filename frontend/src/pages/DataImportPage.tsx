import {
  AlertTriangle,
  ArrowLeft,
  Check,
  FileSpreadsheet,
  FileText,
  Keyboard,
  LoaderCircle,
  Lock,
  RefreshCw,
  SkipForward,
  Upload,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { DragEvent, FormEvent, ReactNode } from 'react'

import {
  Badge,
  Button,
  Checkbox,
  Disclosure,
  EmptyState,
  Panel,
  PanelBody,
  PanelHeader,
  SectionHeader,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  ToastStack,
  useToasts,
} from '@/components/ui'
import { useAuth } from '@/hooks'
import { cn } from '@/lib/cn'
import { formatDateTime, formatNumber } from '@/lib/format'
import {
  confirmImport,
  getImportFields,
  getImportHistory,
  getImportOptions,
  inspectImport,
  inspectManualImport,
  invalidateImportedDatasets,
  isForbidden,
  toErrorMessage,
  triggerNeo4jImport,
  validateImport,
} from '@/services'
import type {
  CnasField,
  ImportBatch,
  ImportEntryOptions,
  ImportHistoryItem,
  ImportMapping,
  ImportPreviewRow,
  ImportSourceKind,
  ImportStatus,
  ManualImportPayload,
} from '@/types'

const SECURITY_NOTICE =
  'Only upload investigative information you are authorized to process.'

const STEPS = [
  { id: 'source', label: 'Source' },
  { id: 'upload', label: 'Upload' },
  { id: 'map', label: 'Map fields' },
  { id: 'preview', label: 'Validate' },
  { id: 'process', label: 'Import' },
  { id: 'results', label: 'Results' },
] as const

type WizardStep = (typeof STEPS)[number]['id']
type InputMode = 'upload' | 'manual'

interface ManualFormState {
  fir_id: string
  date: string
  crime: string
  jurisdiction: string
  investigator: string
  person_id: string
  name: string
  phone: string
  vehicle_no: string
  bank_account: string
  social_id: string
  home_city: string
  location: string
  risk_group: string
  vehicle_type: string
  registered_city: string
  notes: string
}

interface CustomFieldRow {
  key: string
  value: string
}

const EMPTY_MANUAL_FORM: ManualFormState = {
  fir_id: '',
  date: '',
  crime: '',
  jurisdiction: '',
  investigator: '',
  person_id: '',
  name: '',
  phone: '',
  vehicle_no: '',
  bank_account: '',
  social_id: '',
  home_city: '',
  location: '',
  risk_group: '',
  vehicle_type: '',
  registered_city: '',
  notes: '',
}

interface ManualDraft {
  id: string
  form: ManualFormState
  customFields: CustomFieldRow[]
}

function newManualDraft(defaults?: Partial<ManualFormState>): ManualDraft {
  return {
    id:
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `entry-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    form: { ...EMPTY_MANUAL_FORM, ...defaults },
    customFields: [{ key: '', value: '' }],
  }
}

function recordFromDraft(draft: ManualDraft): ManualImportPayload {
  const payload: ManualImportPayload = {}
  for (const [key, value] of Object.entries(draft.form) as Array<
    [keyof ManualFormState, string]
  >) {
    const trimmed = value.trim()
    if (trimmed) payload[key] = trimmed
  }
  const extras = draft.customFields
    .map((item) => ({ key: item.key.trim(), value: item.value.trim() }))
    .filter((item) => item.key && item.value)
  if (extras.length) payload.custom_fields = extras
  return payload
}

const FIELD_CLASS =
  'h-8 w-full rounded-sm border border-line-strong bg-surface-raised px-2 text-xs text-ink focus:border-accent/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-70'

const PROCESS_STAGES = [
  { id: 'uploading', label: 'Uploading' },
  { id: 'validating', label: 'Validating' },
  { id: 'mapping', label: 'Mapping' },
  { id: 'normalizing', label: 'Normalizing' },
  { id: 'extracting', label: 'Extracting' },
  { id: 'resolving', label: 'Resolving' },
  { id: 'graph_preparation', label: 'Graph preparation' },
  { id: 'graph_import', label: 'Graph import' },
  { id: 'complete', label: 'Complete' },
] as const

const STATUS_LABEL: Record<ImportStatus, string> = {
  draft: 'Draft',
  validating: 'Validating',
  ready: 'Ready',
  importing: 'Importing',
  complete: 'Complete',
  completed_with_warnings: 'Completed with warnings',
  partially_imported: 'Partially imported',
  failed: 'Failed',
}

type StageMarkOutcome = 'success' | 'warning' | 'failed' | 'pending'

function resultStageOutcome(
  stageId: string,
  batch: ImportBatch,
): StageMarkOutcome {
  if (stageId === 'complete') {
    if (batch.status === 'complete') return 'success'
    if (batch.status === 'failed') return 'failed'
    if (
      batch.status === 'completed_with_warnings' ||
      batch.status === 'partially_imported'
    ) {
      return 'warning'
    }
    return 'pending'
  }

  const recorded = batch.result?.stage_results?.[stageId]
  if (recorded === 'unavailable') return 'warning'
  if (recorded === 'failed') return 'failed'
  if (recorded === 'complete') return 'success'

  if (stageId === 'graph_import') {
    const graphStatus = batch.result?.graph.status
    if (graphStatus === 'unavailable') return 'warning'
    if (graphStatus === 'failed') return 'failed'
    if (graphStatus === 'imported' || graphStatus === 'dry_run') return 'success'
  }

  const completed = new Set(batch.stages ?? [])
  return completed.has(stageId) ? 'success' : 'pending'
}

function StageMark({ outcome }: { outcome: StageMarkOutcome }) {
  if (outcome === 'success') {
    return <Check size={14} className="text-signal-low" />
  }
  if (outcome === 'warning') {
    return <AlertTriangle size={14} className="text-signal-medium" />
  }
  if (outcome === 'failed') {
    return <AlertTriangle size={14} className="text-signal-critical" />
  }
  return <span className="h-3.5 w-3.5 rounded-full border border-line" />
}

function rowNeedsDecision(
  row: ImportPreviewRow,
  continueWithWarnings: boolean,
): boolean {
  if (row.status === 'skipped') return false
  if (row.status === 'ready' || row.status === 'possible_duplicate') return false
  if (
    (row.status === 'incomplete' || row.status === 'invalid') &&
    row.importable &&
    continueWithWarnings
  ) {
    return false
  }
  return true
}

function unresolvedDecisionMessage(count: number): string {
  const noun = count === 1 ? 'record' : 'records'
  return `${count} ${noun} still require a decision. Mark them as Skip or resolve the issue before continuing.`
}

function mappingPayload(
  mappings: ImportMapping[],
): Record<string, string | null> {
  return Object.fromEntries(
    mappings.map((item) => [item.column, item.cnas_field]),
  )
}

function mappingFingerprint(mappings: ImportMapping[]): string {
  return JSON.stringify(mappingPayload(mappings))
}

function fileInspectKey(
  file: File | null,
  sourceKind: ImportSourceKind,
  jurisdiction: string,
): string | null {
  if (!file) return null
  const scope =
    sourceKind === 'unstructured' ? jurisdiction.trim().toUpperCase() : ''
  return `${file.name}:${file.size}:${file.lastModified}:${sourceKind}:${scope}`
}

function manualInspectKey(entries: ManualDraft[]): string {
  return JSON.stringify(entries.map(recordFromDraft))
}

function rowStatusLabel(status: ImportPreviewRow['status']): string {
  switch (status) {
    case 'ready':
      return 'Mapped'
    case 'incomplete':
      return 'Missing'
    case 'invalid':
      return 'Invalid'
    case 'duplicate':
      return 'Duplicate'
    case 'possible_duplicate':
      return 'Possible match'
    case 'unauthorized':
      return 'Unauthorized'
    case 'skipped':
      return 'Skipped'
    default:
      return status
  }
}

function RowMark({ status }: { status: ImportPreviewRow['status'] }) {
  if (status === 'ready') {
    return <span className="text-signal-low">✓</span>
  }
  if (status === 'unauthorized') {
    return <span className="text-ink-faint">🔒</span>
  }
  if (status === 'invalid') {
    return <span className="text-signal-critical">✕</span>
  }
  return <span className="text-signal-medium">⚠</span>
}

export function DataImportPage() {
  const { canWriteInvestigations, user, isAdmin } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)
  const { toasts, push: pushToast, dismiss } = useToasts()

  const [step, setStep] = useState<WizardStep>('source')
  const [inputMode, setInputMode] = useState<InputMode>('upload')
  const [sourceKind, setSourceKind] = useState<ImportSourceKind>('structured')
  const [jurisdiction, setJurisdiction] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [fields, setFields] = useState<CnasField[]>([])
  const [entryOptions, setEntryOptions] = useState<ImportEntryOptions | null>(
    null,
  )
  const [manualEntries, setManualEntries] = useState<ManualDraft[]>(() => [
    newManualDraft(),
  ])
  const [entryErrors, setEntryErrors] = useState<string[][]>([])
  const [batch, setBatch] = useState<ImportBatch | null>(null)
  const [mappings, setMappings] = useState<ImportMapping[]>([])
  const [skipIndexes, setSkipIndexes] = useState<Set<number>>(new Set())
  const [continueWithWarnings, setContinueWithWarnings] = useState(false)
  const [inspectedSourceKey, setInspectedSourceKey] = useState<string | null>(
    null,
  )
  const [inspectedManualKey, setInspectedManualKey] = useState<string | null>(
    null,
  )
  const [validatedMappingKey, setValidatedMappingKey] = useState<string | null>(
    null,
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<ImportHistoryItem[] | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)

  const reloadHistory = useCallback(async () => {
    try {
      const response = await getImportHistory()
      setHistory(response.data)
      setHistoryError(null)
    } catch (caught) {
      setHistoryError(toErrorMessage(caught))
    }
  }, [])

  useEffect(() => {
    void reloadHistory()
    void getImportFields()
      .then((response) => setFields(response.data))
      .catch(() => setFields([]))
  }, [reloadHistory])

  useEffect(() => {
    if (!canWriteInvestigations) return
    void getImportOptions()
      .then((options) => {
        setEntryOptions(options)
        setManualEntries((current) =>
          current.map((entry) => ({
            ...entry,
            form: {
              ...entry.form,
              investigator:
                entry.form.investigator || options.default_investigator || '',
              jurisdiction:
                entry.form.jurisdiction || options.default_jurisdiction || '',
            },
          })),
        )
      })
      .catch(() => setEntryOptions(null))
  }, [canWriteInvestigations])

  const previewRows = batch?.preview_rows
  const validation = batch?.validation ?? null

  const currentSourceKey = fileInspectKey(file, sourceKind, jurisdiction)
  const currentManualKey = useMemo(
    () => manualInspectKey(manualEntries),
    [manualEntries],
  )
  const currentMappingKey = useMemo(
    () => mappingFingerprint(mappings),
    [mappings],
  )
  const sourceInspectFresh =
    batch != null &&
    batch.source_kind !== 'manual' &&
    inspectedSourceKey != null &&
    inspectedSourceKey === currentSourceKey
  const mappingValidateFresh =
    Boolean(batch?.preview_rows?.length || batch?.validation) &&
    validatedMappingKey != null &&
    validatedMappingKey === currentMappingKey
  const manualInspectFresh =
    batch?.source_kind === 'manual' &&
    inspectedManualKey != null &&
    inspectedManualKey === currentManualKey &&
    Boolean(batch.preview_rows)

  const unauthorizedIndexes = useMemo(
    () =>
      (previewRows ?? [])
        .filter((row) => row.status === 'unauthorized')
        .map((row) => row.index),
    [previewRows],
  )

  const confirmSkips = useMemo(() => [...skipIndexes], [skipIndexes])

  const unresolvedRows = useMemo(
    () =>
      (previewRows ?? []).filter(
        (row) =>
          !skipIndexes.has(row.index) &&
          rowNeedsDecision(row, continueWithWarnings),
      ),
    [previewRows, skipIndexes, continueWithWarnings],
  )

  const resetWizard = () => {
    setStep('source')
    setInputMode('upload')
    setFile(null)
    setBatch(null)
    setMappings([])
    setSkipIndexes(new Set())
    setContinueWithWarnings(false)
    setInspectedSourceKey(null)
    setInspectedManualKey(null)
    setValidatedMappingKey(null)
    setError(null)
    setEntryErrors([])
    setBusy(false)
    setManualEntries([
      newManualDraft({
        investigator: entryOptions?.default_investigator || user?.username || '',
        jurisdiction: entryOptions?.default_jurisdiction || '',
      }),
    ])
  }

  const goBack = () => {
    if (busy) return
    setError(null)
    if (step === 'map') {
      setStep('source')
      return
    }
    if (step === 'preview') {
      if (batch?.source_kind === 'manual' || inputMode === 'manual') {
        setInputMode('manual')
        setStep('source')
        return
      }
      setStep('map')
    }
  }

  const continueToMap = () => {
    if (!sourceInspectFresh || !batch) return
    setError(null)
    setStep('map')
  }

  const continueToPreview = () => {
    if (!mappingValidateFresh || !batch) return
    setError(null)
    setStep('preview')
  }

  const continueToManualPreview = () => {
    if (!manualInspectFresh || !batch) return
    setError(null)
    setStep('preview')
  }

  const onFileChosen = (chosen: File | null) => {
    setFile(chosen)
    setError(null)
  }

  const onDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault()
    setDragOver(false)
    const dropped = event.dataTransfer.files[0]
    if (dropped) onFileChosen(dropped)
  }

  const notifyValidation = (validated: ImportBatch) => {
    const summary = validated.validation
    if (!summary) return
    if (summary.unauthorized > 0) {
      pushToast(
        'error',
        'Authorization error',
        summary.unauthorized_message ??
          'One or more records are outside your authorized jurisdiction.',
      )
    }
    if (summary.duplicates > 0) {
      pushToast(
        'warning',
        'Possible duplicate records',
        `${summary.duplicates} record${summary.duplicates === 1 ? '' : 's'} match an existing case or person. CNAS will not merge them automatically.`,
      )
    }
    if (summary.possible_duplicates > 0) {
      pushToast(
        'warning',
        'Possible person match',
        `${summary.possible_duplicates} record${summary.possible_duplicates === 1 ? '' : 's'} may match an existing person. Importing continues as a new person unless you skip.`,
      )
    }
    if (summary.invalid > 0 || (summary.incomplete > 0 && summary.ready === 0 && summary.possible_duplicates === 0)) {
      pushToast(
        'error',
        'Validation error',
        'CNAS could not represent every record. Review the table, edit the form if this was a manual entry, or skip unresolved rows.',
      )
    } else {
      pushToast(
        'success',
        'Validation complete',
        'Review what CNAS understood before confirming the import.',
      )
    }
  }

  const runInspect = async (event: FormEvent) => {
    event.preventDefault()
    if (!file) {
      setError('Choose a file to inspect.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const inspected = await inspectImport(
        file,
        sourceKind,
        sourceKind === 'unstructured' ? jurisdiction : undefined,
      )
      setBatch(inspected)
      setMappings(inspected.mappings)
      setSkipIndexes(new Set())
      setContinueWithWarnings(false)
      setInspectedSourceKey(fileInspectKey(file, sourceKind, jurisdiction))
      setValidatedMappingKey(null)
      setStep('map')
    } catch (caught) {
      const message = toErrorMessage(caught)
      setError(message)
      pushToast(
        isForbidden(caught) ? 'error' : 'error',
        isForbidden(caught) ? 'Authorization error' : 'Import failure',
        message,
      )
    } finally {
      setBusy(false)
    }
  }

  const buildManualPayload = (): ManualImportPayload => ({
    records: manualEntries.map(recordFromDraft),
  })

  const runInspectManual = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setEntryErrors([])
    try {
      const inspected = await inspectManualImport(buildManualPayload())
      const validated = await validateImport(inspected.id, {
        mappings: mappingPayload(inspected.mappings),
        skip_indexes: [],
      })
      setBatch(validated)
      setMappings(validated.mappings)
      setSkipIndexes(new Set())
      setContinueWithWarnings(false)
      setInspectedManualKey(currentManualKey)
      setValidatedMappingKey(mappingFingerprint(validated.mappings))
      notifyValidation(validated)
      setEntryErrors(
        (validated.preview_rows ?? []).map((row) => row.reasons ?? []),
      )
      setStep('preview')
    } catch (caught) {
      const message = toErrorMessage(caught)
      setError(message)
      setEntryErrors(manualEntries.map(() => [message]))
      pushToast(
        isForbidden(caught) ? 'error' : 'error',
        isForbidden(caught) ? 'Authorization error' : 'Validation error',
        message,
      )
    } finally {
      setBusy(false)
    }
  }

  const runValidate = async () => {
    if (!batch) return
    const mappingsChanged =
      validatedMappingKey != null && validatedMappingKey !== currentMappingKey
    const skipPayload = mappingsChanged ? [] : [...skipIndexes]
    if (mappingsChanged) {
      setSkipIndexes(new Set())
      setContinueWithWarnings(false)
    }
    setBusy(true)
    setError(null)
    try {
      const validated = await validateImport(batch.id, {
        mappings: mappingPayload(mappings),
        skip_indexes: skipPayload,
      })
      setBatch(validated)
      setMappings(validated.mappings)
      setValidatedMappingKey(mappingFingerprint(validated.mappings))
      notifyValidation(validated)
      setStep('preview')
    } catch (caught) {
      const message = toErrorMessage(caught)
      setError(message)
      pushToast('error', 'Validation error', message)
    } finally {
      setBusy(false)
    }
  }

  const runConfirm = async () => {
    if (!batch) return
    if (batch.source_kind === 'manual') {
      if (!manualInspectFresh) {
        const message =
          'The entered records changed. Validate again before importing.'
        setError(message)
        setInputMode('manual')
        setStep('source')
        pushToast('warning', 'Review required', message)
        return
      }
    } else {
      if (!sourceInspectFresh) {
        const message =
          'The file or source type changed. Detect the schema again before importing.'
        setError(message)
        setStep('source')
        pushToast('warning', 'Review required', message)
        return
      }
      if (!mappingValidateFresh) {
        const message =
          'Field mapping changed. Validate records again before importing.'
        setError(message)
        setStep('map')
        pushToast('warning', 'Review required', message)
        return
      }
    }
    if (unresolvedRows.length > 0) {
      const message = unresolvedDecisionMessage(unresolvedRows.length)
      setError(message)
      pushToast('warning', 'Records require a decision', message)
      return
    }
    setBusy(true)
    setError(null)
    setStep('process')
    try {
      const imported = await confirmImport(batch.id, {
        mappings: mappingPayload(mappings),
        skip_indexes: confirmSkips,
        continue_with_warnings: continueWithWarnings,
      })
      setBatch(imported)
      setStep('results')
      const result = imported.result
      if (result?.imported === 0 && (result.skipped ?? 0) > 0) {
        pushToast(
          'success',
          'Import finished',
          result.notice ??
            'No new records were added because all records were skipped.',
        )
      } else if (imported.status === 'failed') {
        pushToast('error', 'Import failure', 'No records could be imported.')
      } else {
        pushToast(
          'success',
          'Import complete',
          `${result?.imported ?? 0} record${(result?.imported ?? 0) === 1 ? '' : 's'} added to People and Cases.`,
        )
      }
      invalidateImportedDatasets()
      await reloadHistory()
    } catch (caught) {
      const message = toErrorMessage(caught)
      setError(message)
      setStep('preview')
      pushToast(
        isForbidden(caught) ? 'error' : 'error',
        isForbidden(caught) ? 'Authorization error' : 'Import failure',
        message,
      )
    } finally {
      setBusy(false)
    }
  }

  const skipUnauthorized = () => {
    setSkipIndexes((current) => {
      const next = new Set(current)
      for (const index of unauthorizedIndexes) next.add(index)
      return next
    })
  }

  const toggleSkip = (index: number) => {
    setSkipIndexes((current) => {
      const next = new Set(current)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  if (!canWriteInvestigations) {
    return (
      <div className="space-y-4">
        <SectionHeader
          eyebrow="Ingestion"
          title="Data Import"
          description="Upload investigative tables or narratives into the existing CNAS pipeline."
        />
        <Panel>
          <EmptyState
            icon={<Lock size={16} strokeWidth={1.75} />}
            title="Import is restricted"
            description="Your role can review CNAS data but cannot upload investigative files. Ask an analyst or administrator."
          />
        </Panel>
        <HistoryPanel items={history} error={historyError} onReload={reloadHistory} />
      </div>
    )
  }

  const stepIndex = STEPS.findIndex((item) => item.id === step)

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Ingestion"
        title="Data Import"
        description="Inspect unfamiliar investigative files, map what CNAS understands, and import into the same People, Cases, and graph pipeline as preloaded data."
      />

      <p className="text-2xs tracking-wide text-ink-faint">{SECURITY_NOTICE}</p>

      <ol className="flex flex-wrap gap-2">
        {STEPS.map((item, index) => {
          const active = item.id === step
          const done = index < stepIndex
          return (
            <li
              key={item.id}
              className={cn(
                'flex items-center gap-2 rounded-sm border px-2.5 py-1 text-2xs font-medium tracking-wide uppercase',
                active
                  ? 'border-accent/50 bg-accent/10 text-accent'
                  : done
                    ? 'border-line bg-surface-raised text-ink'
                    : 'border-line text-ink-faint',
              )}
            >
              <span className="font-mono tabular-nums">{index + 1}</span>
              {item.label}
            </li>
          )
        })}
      </ol>

      {error ? (
        <Panel className="border-signal-critical/40">
          <PanelBody>
            <p className="text-sm text-signal-critical">{error}</p>
          </PanelBody>
        </Panel>
      ) : null}

      {step === 'source' || step === 'upload' ? (
        <Panel>
          <PanelHeader
            eyebrow="Source"
            title="Choose how records enter CNAS"
            description="Upload a file or enter a case-centered investigative record. Both paths use the same validation, review, and import pipeline."
          />
          <PanelBody className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <SourceCard
                active={inputMode === 'upload'}
                icon={<Upload size={16} strokeWidth={1.75} />}
                title="Upload File"
                detail="CSV, JSON, Excel, or unstructured narrative. Detect schema, map fields, then review."
                onClick={() => {
                  if (inputMode === 'upload') return
                  setInputMode('upload')
                  setError(null)
                }}
              />
              <SourceCard
                active={inputMode === 'manual'}
                icon={<Keyboard size={16} strokeWidth={1.75} />}
                title="Enter Data Manually"
                detail="Create a case/FIR-centered investigative record. CNAS validates it before anything is imported."
                onClick={() => {
                  if (inputMode === 'manual') return
                  setInputMode('manual')
                  setError(null)
                }}
              />
            </div>

            {inputMode === 'upload' ? (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  <SourceCard
                    active={sourceKind === 'structured'}
                    icon={<FileSpreadsheet size={16} strokeWidth={1.75} />}
                    title="Structured table"
                    detail="CSV, JSON array of objects, or Excel (.xlsx)."
                    onClick={() => {
                      if (sourceKind === 'structured') return
                      setSourceKind('structured')
                      setError(null)
                    }}
                  />
                  <SourceCard
                    active={sourceKind === 'unstructured'}
                    icon={<FileText size={16} strokeWidth={1.75} />}
                    title="Unstructured narrative"
                    detail="Plain text, Markdown, or JSON with a text field. Uses the existing FIR extraction pipeline."
                    onClick={() => {
                      if (sourceKind === 'unstructured') return
                      setSourceKind('unstructured')
                      setError(null)
                    }}
                  />
                </div>

                {sourceKind === 'unstructured' ? (
                  <label className="block max-w-sm">
                    <span className="mb-1 block text-2xs tracking-wide text-ink-faint uppercase">
                      Jurisdiction (required for extraction)
                    </span>
                    <input
                      value={jurisdiction}
                      onChange={(event) => setJurisdiction(event.target.value)}
                      placeholder="e.g. DEL"
                      className={FIELD_CLASS}
                    />
                  </label>
                ) : null}

                <form onSubmit={runInspect} className="space-y-3">
                  <button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    onDragOver={(event) => {
                      event.preventDefault()
                      setDragOver(true)
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={onDrop}
                    className={cn(
                      'flex min-h-44 w-full flex-col items-center justify-center gap-2 rounded-md border border-dashed px-6 py-10 text-center transition-colors',
                      dragOver
                        ? 'border-accent bg-accent/10'
                        : 'border-line-strong bg-surface-raised hover:border-accent/50',
                    )}
                  >
                    <Upload size={22} strokeWidth={1.6} className="text-accent" />
                    <p className="text-sm font-medium text-ink">
                      Drop a file here, or click to browse
                    </p>
                    <p className="max-w-md text-xs text-ink-muted">
                      {sourceKind === 'structured'
                        ? 'Accepted: CSV, JSON, Excel (.xlsx). Column names do not need to match CNAS.'
                        : 'Accepted: .txt, .md, or JSON with a text field. PDF and images are not parsed.'}
                    </p>
                    {file ? (
                      <p className="font-mono text-xs text-ink">
                        {file.name} · {Math.max(1, Math.round(file.size / 1024))} KB
                      </p>
                    ) : null}
                  </button>
                  <input
                    ref={inputRef}
                    type="file"
                    className="sr-only"
                    accept={
                      sourceKind === 'structured'
                        ? '.csv,.json,.xlsx,application/json,text/csv'
                        : '.txt,.md,.json,text/plain,application/json'
                    }
                    onChange={(event) =>
                      onFileChosen(event.target.files?.[0] ?? null)
                    }
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    {sourceInspectFresh ? (
                      <Button
                        type="button"
                        variant="primary"
                        onClick={continueToMap}
                        disabled={busy}
                      >
                        Continue to mapping
                      </Button>
                    ) : null}
                    <Button
                      type="submit"
                      variant={sourceInspectFresh ? 'secondary' : 'primary'}
                      disabled={busy || !file}
                    >
                      {busy
                        ? 'Inspecting…'
                        : sourceInspectFresh
                          ? 'Detect schema again'
                          : 'Detect schema'}
                    </Button>
                    {file ? (
                      <Button
                        variant="ghost"
                        onClick={() => onFileChosen(null)}
                        disabled={busy}
                      >
                        Clear file
                      </Button>
                    ) : null}
                  </div>
                </form>
              </>
            ) : (
              <form
                onSubmit={(event) => void runInspectManual(event)}
                className="space-y-4"
              >
                <p className="text-xs text-ink-muted">
                  Each entry is a case-centered investigative record. Add as
                  many as you need; CNAS validates the whole batch before
                  anything is imported.
                </p>
                {manualEntries.map((entry, index) => (
                  <ManualEntryForm
                    key={entry.id}
                    index={index}
                    total={manualEntries.length}
                    form={entry.form}
                    customFields={entry.customFields}
                    options={entryOptions}
                    errors={entryErrors[index] ?? []}
                    busy={busy}
                    lockedInvestigator={!isAdmin}
                    lockedJurisdiction={Boolean(
                      entryOptions?.jurisdiction_locked,
                    )}
                    onChange={(patch) =>
                      setManualEntries((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index
                            ? { ...item, form: { ...item.form, ...patch } }
                            : item,
                        ),
                      )
                    }
                    onCustomFieldsChange={(rows) =>
                      setManualEntries((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index
                            ? { ...item, customFields: rows }
                            : item,
                        ),
                      )
                    }
                    {...(manualEntries.length > 1
                      ? {
                          onRemove: () =>
                            setManualEntries((current) =>
                              current.filter(
                                (_, itemIndex) => itemIndex !== index,
                              ),
                            ),
                        }
                      : {})}
                  />
                ))}
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={busy}
                    onClick={() =>
                      setManualEntries((current) => [
                        ...current,
                        newManualDraft({
                          investigator:
                            entryOptions?.default_investigator ||
                            user?.username ||
                            '',
                          jurisdiction:
                            entryOptions?.default_jurisdiction || '',
                        }),
                      ])
                    }
                  >
                    Add another record
                  </Button>
                  {manualInspectFresh ? (
                    <Button
                      type="button"
                      variant="primary"
                      onClick={continueToManualPreview}
                      disabled={busy}
                    >
                      Continue to review
                    </Button>
                  ) : null}
                  <Button
                    type="submit"
                    variant={manualInspectFresh ? 'secondary' : 'primary'}
                    disabled={busy}
                  >
                    {busy
                      ? 'Validating…'
                      : manualInspectFresh
                        ? 'Validate again'
                        : `Validate ${manualEntries.length} record${manualEntries.length === 1 ? '' : 's'}`}
                  </Button>
                  <p className="text-xs text-ink-muted">
                    Nothing is imported until you review and confirm.
                  </p>
                </div>
              </form>
            )}
          </PanelBody>
        </Panel>
      ) : null}

      {step === 'map' && batch ? (
        <Panel>
          <PanelHeader
            eyebrow={batch.filename}
            title="Map uploaded columns"
            description="CNAS guessed what it recognises. Unmapped fields are retained as source data — they are not discarded."
            actions={
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  icon={<ArrowLeft size={13} strokeWidth={1.75} />}
                  onClick={goBack}
                  disabled={busy}
                >
                  Back
                </Button>
                {mappingValidateFresh ? (
                  <Button
                    variant="primary"
                    onClick={continueToPreview}
                    disabled={busy}
                  >
                    Continue
                  </Button>
                ) : null}
                <Button
                  variant={mappingValidateFresh ? 'secondary' : 'primary'}
                  onClick={() => void runValidate()}
                  disabled={busy}
                >
                  {busy ? 'Validating…' : 'Validate records'}
                </Button>
              </div>
            }
          />
          <Table>
            <TableHeader>
              <TableRow>
                <TableHeaderCell>Uploaded column</TableHeaderCell>
                <TableHeaderCell>Sample values</TableHeaderCell>
                <TableHeaderCell>CNAS field</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mappings.map((mapping) => (
                <TableRow key={mapping.column}>
                  <TableCell mono>{mapping.column}</TableCell>
                  <TableCell className="max-w-xs truncate text-ink-muted">
                    {(batch.samples[mapping.column] ?? []).join(' · ') || '—'}
                  </TableCell>
                  <TableCell>
                    <select
                      value={mapping.cnas_field ?? 'unmapped'}
                      onChange={(event) => {
                        const value = event.target.value
                        setMappings((current) =>
                          current.map((item) =>
                            item.column === mapping.column
                              ? {
                                  ...item,
                                  cnas_field: value === 'unmapped' ? null : value,
                                  status:
                                    value === 'unmapped' ? 'unmapped' : 'mapped',
                                  method: 'user',
                                  notice:
                                    value === 'unmapped'
                                      ? 'CNAS does not currently map this field. The original value will be retained as source data where supported.'
                                      : null,
                                }
                              : item,
                          ),
                        )
                      }}
                      className="h-8 min-w-48 rounded-sm border border-line-strong bg-surface-raised px-2 text-xs text-ink focus:border-accent/60 focus:outline-none"
                    >
                      <option value="unmapped">Do not map (retain source)</option>
                      {fields.map((field) => (
                        <option key={field.id} value={field.id}>
                          {field.label}
                        </option>
                      ))}
                    </select>
                  </TableCell>
                  <TableCell>
                    {mapping.cnas_field ? (
                      <Badge tone="low">
                        mapped · {Math.round(mapping.confidence * 100)}%
                      </Badge>
                    ) : (
                      <Badge tone="medium">unmapped</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <PanelBody>
            <p className="text-xs text-ink-muted">
              You do not need to map every column. Officer, weapon, notes and other
              extra fields stay on the import as source data.
            </p>
          </PanelBody>
        </Panel>
      ) : null}

      {step === 'preview' && batch ? (
        <Panel>
          <PanelHeader
            eyebrow="Validation"
            title={`${formatNumber(validation?.detected ?? batch.row_count)} records detected`}
            description={
              validation?.unauthorized_message ??
              'Incomplete records can continue with warnings when they still carry enough identity. CNAS will not invent missing values.'
            }
            actions={
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  icon={<ArrowLeft size={13} strokeWidth={1.75} />}
                  onClick={goBack}
                  disabled={busy}
                >
                  Back
                </Button>
                {unauthorizedIndexes.length > 0 ? (
                  <Button
                    size="sm"
                    icon={<SkipForward size={13} strokeWidth={1.75} />}
                    onClick={skipUnauthorized}
                  >
                    Skip unauthorized
                  </Button>
                ) : null}
                <Button
                  variant="primary"
                  onClick={() => void runConfirm()}
                  disabled={busy}
                >
                  Confirm import
                </Button>
              </div>
            }
          />
          <div className="grid gap-px border-b border-line bg-line sm:grid-cols-6">
            <Stat label="Ready" value={validation?.ready ?? 0} tone="low" />
            <Stat label="Incomplete" value={validation?.incomplete ?? 0} tone="medium" />
            <Stat
              label="Possible matches"
              value={validation?.possible_duplicates ?? 0}
              tone="medium"
            />
            <Stat label="Duplicates" value={validation?.duplicates ?? 0} tone="high" />
            <Stat
              label="Unauthorized"
              value={validation?.unauthorized ?? 0}
              tone="critical"
            />
            <Stat
              label="Needs decision"
              value={unresolvedRows.length}
              tone={unresolvedRows.length ? 'critical' : 'low'}
            />
          </div>
          <PanelBody className="space-y-3">
            <Checkbox
              label="Continue with warnings where records are still representable"
              checked={continueWithWarnings}
              onChange={setContinueWithWarnings}
            />
            <p className="text-xs text-ink-muted">
              Possible matches are imported as new persons. CNAS never merges
              similar identities automatically.
            </p>
          </PanelBody>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHeaderCell className="w-10" />
                <TableHeaderCell>Row</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Understood</TableHeaderCell>
                <TableHeaderCell>Attention</TableHeaderCell>
                <TableHeaderCell>Skip</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(previewRows ?? []).map((row) => (
                <TableRow key={row.index}>
                  <TableCell>
                    <RowMark status={row.status} />
                  </TableCell>
                  <TableCell mono>{row.index + 1}</TableCell>
                  <TableCell>{rowStatusLabel(row.status)}</TableCell>
                  <TableCell className="max-w-sm truncate text-ink-muted">
                    {row.redacted
                      ? 'Contents withheld — outside your jurisdiction.'
                      : Object.entries(row.mapped)
                          .filter(([, value]) => value)
                          .map(([key, value]) => `${key}: ${value}`)
                          .join(' · ') || '—'}
                  </TableCell>
                  <TableCell className="max-w-xs text-ink-muted">
                    {row.reasons[0] ??
                      (Object.keys(row.unmapped).length
                        ? 'Unmapped fields retained as source data.'
                        : '—')}
                  </TableCell>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={skipIndexes.has(row.index)}
                      onChange={() => toggleSkip(row.index)}
                      aria-label={`Skip row ${row.index + 1}`}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>
      ) : null}

      {step === 'process' ? (
        <Panel>
          <PanelHeader
            title="Processing import"
            description="Stages reflect work the backend actually runs. Percentages are not estimated."
          />
          <PanelBody>
            <ol className="space-y-2">
              {PROCESS_STAGES.map((stage, index) => {
                const reached = PROCESS_STAGES.findIndex((item) => item.id === 'normalizing')
                const current = index <= reached
                return (
                  <li key={stage.id} className="flex items-center gap-2 text-xs">
                    {current ? (
                      index === reached ? (
                        <LoaderCircle
                          size={14}
                          className="animate-spin text-accent"
                        />
                      ) : (
                        <Check size={14} className="text-signal-low" />
                      )
                    ) : (
                      <span className="h-3.5 w-3.5 rounded-full border border-line" />
                    )}
                    <span className={current ? 'text-ink' : 'text-ink-faint'}>
                      {stage.label}
                    </span>
                  </li>
                )
              })}
            </ol>
          </PanelBody>
        </Panel>
      ) : null}

      {step === 'results' && batch ? (
        <ResultsPanel batch={batch} onReset={resetWizard} />
      ) : null}

      <HistoryPanel items={history} error={historyError} onReload={reloadHistory} />
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </div>
  )
}

function ManualEntryForm({
  index,
  total,
  form,
  customFields,
  options,
  errors,
  busy,
  lockedInvestigator,
  lockedJurisdiction,
  onChange,
  onCustomFieldsChange,
  onRemove,
}: {
  index: number
  total: number
  form: ManualFormState
  customFields: CustomFieldRow[]
  options: ImportEntryOptions | null
  errors: string[]
  busy: boolean
  lockedInvestigator: boolean
  lockedJurisdiction: boolean
  onChange: (patch: Partial<ManualFormState>) => void
  onCustomFieldsChange: (rows: CustomFieldRow[]) => void
  onRemove?: () => void
}) {
  const jurisdictions = options?.jurisdictions ?? []
  const investigators = options?.investigators ?? []
  const crimes = options?.crimes ?? []

  return (
    <div className="space-y-4 rounded-md border border-line bg-surface-raised p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Entry {index + 1} of {total}
        </p>
        {onRemove ? (
          <Button
            size="sm"
            variant="ghost"
            disabled={busy}
            onClick={onRemove}
          >
            Remove
          </Button>
        ) : null}
      </div>

      {errors.length > 0 ? (
        <div className="rounded-sm border border-signal-critical/40 bg-signal-critical/8 px-3 py-2">
          <p className="text-2xs tracking-wide text-signal-critical uppercase">
            Validation · Entry {index + 1}
          </p>
          <ul className="mt-1 space-y-1 text-xs text-signal-critical">
            {errors.slice(0, 6).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <fieldset className="space-y-3">
        <legend className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Case / Investigation
        </legend>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Case / FIR ID">
            <input
              value={form.fir_id}
              onChange={(event) => onChange({ fir_id: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Incident / Case Date">
            <input
              type="date"
              value={form.date}
              onChange={(event) => onChange({ date: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Crime / Crime Type">
            <input
              list={`cnas-crime-aliases-${index}`}
              value={form.crime}
              onChange={(event) => onChange({ crime: event.target.value })}
              placeholder="e.g. cyber bullying"
              className={FIELD_CLASS}
            />
            <datalist id={`cnas-crime-aliases-${index}`}>
              {crimes.map((crime) => (
                <option key={crime} value={crime} />
              ))}
            </datalist>
          </Field>
          <Field label="Jurisdiction">
            <select
              value={form.jurisdiction}
              onChange={(event) => onChange({ jurisdiction: event.target.value })}
              disabled={lockedJurisdiction}
              className={FIELD_CLASS}
            >
              {lockedJurisdiction ? null : (
                <option value="">Select jurisdiction</option>
              )}
              {jurisdictions.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Investigator">
            {lockedInvestigator ? (
              <input
                value={form.investigator}
                disabled
                className={FIELD_CLASS}
              />
            ) : (
              <select
                value={form.investigator}
                onChange={(event) =>
                  onChange({ investigator: event.target.value })
                }
                className={FIELD_CLASS}
              >
                {investigators.map((item) => (
                  <option key={item.id} value={item.username}>
                    {item.username}
                  </option>
                ))}
              </select>
            )}
          </Field>
        </div>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Person
        </legend>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Person ID">
            <input
              value={form.person_id}
              onChange={(event) => onChange({ person_id: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Full Name">
            <input
              value={form.name}
              onChange={(event) => onChange({ name: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Phone">
            <input
              value={form.phone}
              onChange={(event) => onChange({ phone: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Vehicle">
            <input
              value={form.vehicle_no}
              onChange={(event) => onChange({ vehicle_no: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Bank account">
            <input
              value={form.bank_account}
              onChange={(event) =>
                onChange({ bank_account: event.target.value })
              }
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Social account">
            <input
              value={form.social_id}
              onChange={(event) => onChange({ social_id: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Home city">
            <input
              value={form.home_city}
              onChange={(event) => onChange({ home_city: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Location">
            <input
              value={form.location}
              onChange={(event) => onChange({ location: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Vehicle type">
            <input
              value={form.vehicle_type}
              onChange={(event) =>
                onChange({ vehicle_type: event.target.value })
              }
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Vehicle registered city">
            <input
              value={form.registered_city}
              onChange={(event) =>
                onChange({ registered_city: event.target.value })
              }
              className={FIELD_CLASS}
            />
          </Field>
          <Field label="Risk group">
            <input
              value={form.risk_group}
              onChange={(event) => onChange({ risk_group: event.target.value })}
              className={FIELD_CLASS}
            />
          </Field>
        </div>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Additional information
        </legend>
        <Field label="Investigator Notes">
          <textarea
            value={form.notes}
            onChange={(event) => onChange({ notes: event.target.value })}
            rows={4}
            className="w-full rounded-sm border border-line-strong bg-surface-raised px-2 py-1.5 text-xs text-ink focus:border-accent/60 focus:outline-none"
            placeholder="Useful context that has no dedicated field."
          />
        </Field>
        <div className="space-y-2">
          <p className="text-2xs tracking-wide text-ink-faint uppercase">
            Custom fields (retained as source data)
          </p>
          {customFields.map((item, index) => (
            <div key={index} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
              <input
                value={item.key}
                onChange={(event) => {
                  const next = customFields.map((row, rowIndex) =>
                    rowIndex === index ? { ...row, key: event.target.value } : row,
                  )
                  onCustomFieldsChange(next)
                }}
                placeholder="Field name"
                className={FIELD_CLASS}
              />
              <input
                value={item.value}
                onChange={(event) => {
                  const next = customFields.map((row, rowIndex) =>
                    rowIndex === index
                      ? { ...row, value: event.target.value }
                      : row,
                  )
                  onCustomFieldsChange(next)
                }}
                placeholder="Value"
                className={FIELD_CLASS}
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  onCustomFieldsChange(
                    customFields.filter((_, rowIndex) => rowIndex !== index),
                  )
                }
              >
                Remove
              </Button>
            </div>
          ))}
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              onCustomFieldsChange([...customFields, { key: '', value: '' }])
            }
          >
            Add custom field
          </Button>
        </div>
      </fieldset>
    </div>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-2xs tracking-wide text-ink-faint uppercase">
        {label}
      </span>
      {children}
    </label>
  )
}

function SourceCard({
  active,
  icon,
  title,
  detail,
  onClick,
}: {
  active: boolean
  icon: ReactNode
  title: string
  detail: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-md border px-4 py-3 text-left transition-colors',
        active
          ? 'border-accent/50 bg-accent/10'
          : 'border-line bg-surface-raised hover:border-line-strong',
      )}
    >
      <span className="mb-2 inline-flex text-accent">{icon}</span>
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 text-xs leading-relaxed text-ink-muted">{detail}</p>
    </button>
  )
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'low' | 'medium' | 'high' | 'critical'
}) {
  return (
    <div className="bg-surface px-4 py-3">
      <p className="text-2xs tracking-wide text-ink-faint uppercase">{label}</p>
      <p
        className={cn(
          'mt-1 font-mono text-lg tabular-nums',
          tone === 'low' && 'text-signal-low',
          tone === 'medium' && 'text-signal-medium',
          tone === 'high' && 'text-signal-high',
          tone === 'critical' && 'text-signal-critical',
        )}
      >
        {formatNumber(value)}
      </p>
    </div>
  )
}

function graphImportStage(
  status: string | null | undefined,
): 'complete' | 'unavailable' | 'failed' | undefined {
  if (status === 'imported' || status === 'dry_run') return 'complete'
  if (status === 'unavailable') return 'unavailable'
  if (status === 'failed') return 'failed'
  return undefined
}

function ResultsPanel({
  batch,
  onReset,
}: {
  batch: ImportBatch
  onReset: () => void
}) {
  const result = batch.result
  const [graph, setGraph] = useState(result?.graph ?? null)
  const [retrying, setRetrying] = useState(false)
  const [retryDetail, setRetryDetail] = useState<string | null>(null)

  const graphStatus = graph?.status ?? result?.graph.status ?? null
  const graphWarning =
    graph && 'warning' in graph ? graph.warning : result?.graph.warning
  const canRetryGraph =
    graphStatus === 'failed' || graphStatus === 'unavailable'

  const graphStage = graphImportStage(graphStatus)
  const displayBatch: ImportBatch = {
    ...batch,
    result: result
      ? {
          ...result,
          graph: graph ?? result.graph,
          ...(graphStage
            ? {
                stage_results: {
                  ...result.stage_results,
                  graph_import: graphStage,
                },
              }
            : {}),
        }
      : result,
  }

  const retryGraphImport = async () => {
    setRetrying(true)
    setRetryDetail(null)
    try {
      const imported = await triggerNeo4jImport(false)
      if (imported.status === 'imported' || imported.status === 'dry_run') {
        setGraph({
          status: imported.status,
          nodes: imported.nodes ?? null,
          relationships: imported.relationships ?? null,
          detail: imported.detail ?? null,
          warning: null,
        })
        return
      }
      setGraph({
        status: imported.status,
        nodes: imported.nodes ?? null,
        relationships: imported.relationships ?? null,
        detail: imported.detail ?? null,
        warning:
          imported.status === 'unavailable'
            ? 'Graph import did not complete because the graph store is unavailable. Retry graph import once it is available.'
            : 'Graph import did not complete; retry graph import once the graph store is available.',
      })
      setRetryDetail(imported.detail ?? 'Graph import did not complete.')
    } catch (caught) {
      const message = toErrorMessage(caught)
      setRetryDetail(message)
    } finally {
      setRetrying(false)
    }
  }

  return (
    <Panel>
      <PanelHeader
        eyebrow={STATUS_LABEL[batch.status]}
        title="Import finished"
        description={
          result?.notice
            ? result.notice
            : 'Successful records are now part of People and Cases / FIRs. Graph import is reported separately and is not marked complete unless the graph store accepted the plan.'
        }
        actions={<Button onClick={onReset}>New import</Button>}
      />
      <div className="grid gap-px border-b border-line bg-line sm:grid-cols-4">
        <Stat label="Imported" value={result?.imported ?? 0} tone="low" />
        <Stat label="Skipped" value={result?.skipped ?? 0} tone="medium" />
        <Stat label="Failed" value={result?.failed ?? 0} tone="critical" />
        <Stat label="Warnings" value={result?.warnings ?? 0} tone="high" />
      </div>
      <PanelBody className="space-y-4">
        {result?.notice || graphWarning ? (
          <p className="flex gap-2 text-xs text-signal-medium">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            {result?.notice ?? graphWarning}
          </p>
        ) : null}
        {retryDetail ? (
          <p className="text-xs text-signal-critical">{retryDetail}</p>
        ) : null}
        {canRetryGraph ? (
          <Button
            size="sm"
            onClick={() => void retryGraphImport()}
            disabled={retrying}
            icon={
              <RefreshCw
                size={13}
                strokeWidth={1.75}
                className={retrying ? 'animate-spin' : undefined}
              />
            }
          >
            {retrying ? 'Retrying graph import…' : 'Retry graph import'}
          </Button>
        ) : null}
        <ol className="grid gap-1 sm:grid-cols-2">
          {PROCESS_STAGES.map((stage) => {
            const outcome = resultStageOutcome(stage.id, displayBatch)
            const label =
              stage.id === 'complete'
                ? STATUS_LABEL[batch.status]
                : stage.label
            return (
              <li key={stage.id} className="flex items-center gap-2 text-xs text-ink">
                <StageMark outcome={outcome} />
                {label}
              </li>
            )
          })}
        </ol>
        {result?.skipped_rows.length ? (
          <div>
            <p className="mb-1 text-2xs tracking-wide text-ink-faint uppercase">
              Skipped
            </p>
            <ul className="space-y-1 text-xs text-ink-muted">
              {result.skipped_rows.slice(0, 12).map((row) => (
                <li key={row.index}>
                  Row {row.index + 1}: {row.reasons[0] ?? row.status}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {result?.failed_rows.length ? (
          <div>
            <p className="mb-1 text-2xs tracking-wide text-ink-faint uppercase">
              Failed
            </p>
            <ul className="space-y-1 text-xs text-ink-muted">
              {result.failed_rows.map((row) => (
                <li key={row.index ?? row.detail}>
                  {row.index != null ? `Row ${row.index + 1}: ` : ''}
                  {row.reasons[0]}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {result?.provenance ? (
          <Disclosure
            title="Provenance"
            subtitle={`${result.provenance.source_file} · ${result.provenance.extraction_method} · ${result.queued_reviews} review(s) queued`}
          >
            <dl className="grid gap-2 sm:grid-cols-2">
              <div>
                <dt className="text-ink-faint">Import ID</dt>
                <dd className="font-mono text-ink">{result.provenance.import_id}</dd>
              </div>
              <div>
                <dt className="text-ink-faint">Uploader</dt>
                <dd className="text-ink">
                  {result.provenance.uploader_username ?? '—'}
                </dd>
              </div>
              <div>
                <dt className="text-ink-faint">Timestamp</dt>
                <dd className="text-ink">
                  {formatDateTime(result.provenance.timestamp)}
                </dd>
              </div>
              <div>
                <dt className="text-ink-faint">Graph</dt>
                <dd className="text-ink">{graphStatus ?? result.graph.status ?? '—'}</dd>
              </div>
            </dl>
          </Disclosure>
        ) : null}
        {batch.limitation ? (
          <p className="text-2xs text-ink-faint">{batch.limitation}</p>
        ) : null}
      </PanelBody>
    </Panel>
  )
}

function HistoryPanel({
  items,
  error,
  onReload,
}: {
  items: ImportHistoryItem[] | null
  error: string | null
  onReload: () => void
}) {
  return (
    <Panel>
      <PanelHeader
        eyebrow="Batches"
        title="Import history"
        description="Draft, validating, ready, importing, complete, completed with warnings, partially imported, and failed. Rollback is not offered — graph MERGE cannot be safely reversed."
        actions={
          <Button size="sm" onClick={onReload}>
            Refresh
          </Button>
        }
      />
      {error ? (
        <EmptyState title="Could not load import history" description={error} />
      ) : items == null ? (
        <EmptyState title="Loading history" />
      ) : items.length === 0 ? (
        <EmptyState
          title="No imports yet"
          description="Completed and in-progress batches will appear here."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHeaderCell>Dataset</TableHeaderCell>
              <TableHeaderCell>Uploaded</TableHeaderCell>
              <TableHeaderCell>Uploader</TableHeaderCell>
              <TableHeaderCell>Records</TableHeaderCell>
              <TableHeaderCell>Status</TableHeaderCell>
              <TableHeaderCell>Outcome</TableHeaderCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <TableCell>
                  <span className="block text-ink">{item.filename}</span>
                  <span className="font-mono text-2xs text-ink-faint">
                    {item.format} · {item.kind}
                  </span>
                </TableCell>
                <TableCell className="whitespace-nowrap text-ink-muted">
                  {formatDateTime(item.created_at)}
                </TableCell>
                <TableCell>{item.uploader_username}</TableCell>
                <TableCell mono>{formatNumber(item.row_count)}</TableCell>
                <TableCell>
                  <Badge
                    tone={
                      item.status === 'failed'
                        ? 'critical'
                        : item.status === 'complete'
                          ? 'low'
                          : 'medium'
                    }
                  >
                    {STATUS_LABEL[item.status]}
                  </Badge>
                </TableCell>
                <TableCell className="text-ink-muted">
                  {item.imported == null
                    ? '—'
                    : `${item.imported} imported · ${item.skipped ?? 0} skipped · ${item.failed ?? 0} failed`}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Panel>
  )
}
