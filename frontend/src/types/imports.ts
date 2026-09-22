/** Types for `/imports` — the data import / upload workflow. */

export type ImportSourceKind = 'structured' | 'unstructured' | 'manual'

export type ImportStatus =
  | 'draft'
  | 'validating'
  | 'ready'
  | 'importing'
  | 'complete'
  | 'completed_with_warnings'
  | 'partially_imported'
  | 'failed'

export type ImportRowStatus =
  | 'ready'
  | 'incomplete'
  | 'invalid'
  | 'duplicate'
  | 'possible_duplicate'
  | 'unauthorized'
  | 'skipped'
  | 'failed'

export interface CnasField {
  id: string
  label: string
  group: string
  description: string
}

export interface ImportMapping {
  column: string
  cnas_field: string | null
  confidence: number
  status: 'mapped' | 'unmapped'
  method: string
  suggested_field?: string | null
  notice: string | null
}

export interface ImportPossibleMatch {
  entity_id?: string | null
  proposed_entity_ids?: string[]
  confidence?: number | null
  method?: string | null
  ambiguous?: boolean
}

export interface ImportPreviewRow {
  index: number
  status: ImportRowStatus
  reasons: string[]
  flags?: string[]
  mapped: Record<string, string | null>
  unmapped: Record<string, string>
  jurisdiction: string | null
  possible_match: ImportPossibleMatch | null
  person_key: string | null
  redacted: boolean
  importable?: boolean
  disposition?: 'import' | 'skipped' | 'unresolved' | 'failed'
  unmapped_notice: string | null
}

export interface ImportValidationSummary {
  detected: number
  ready: number
  incomplete: number
  invalid: number
  duplicates: number
  possible_duplicates: number
  unauthorized: number
  skipped: number
  unmapped_columns: string[]
  unauthorized_message: string | null
  blocking_unauthorized: boolean
  blocking_unresolved?: boolean
  unresolved?: number
  can_continue_with_warnings: boolean
}

export interface ImportGraphResult {
  status: string | null
  nodes?: number | null
  relationships?: number | null
  detail?: string | null
  warning?: string | null
}

export type ImportStageOutcome = 'complete' | 'unavailable' | 'failed'

export interface ImportResult {
  imported: number
  skipped: number
  failed: number
  warnings: number
  queued_reviews: number
  persons: number
  firs: number
  vehicles: number
  graph: ImportGraphResult
  stage_results?: Record<string, ImportStageOutcome>
  notice?: string | null
  failed_rows: Array<{
    index?: number
    status: string
    reasons: string[]
    detail?: string
  }>
  warning_reasons: Array<{
    index?: number | null
    status: string
    reasons: string[]
  }>
  skipped_rows: Array<{
    index: number
    status: string
    reasons: string[]
    redacted?: boolean
  }>
  provenance: {
    import_id: string
    source_file: string
    uploader_id: string | null
    uploader_username: string | null
    timestamp: string
    extraction_method: string
    records: Array<Record<string, unknown>>
  }
}

export interface ImportBatch {
  id: string
  filename: string
  format: string
  kind: ImportSourceKind
  source_kind: ImportSourceKind
  status: ImportStatus
  row_count: number
  created_at: string
  updated_at: string
  uploader_id?: string
  uploader_username: string
  columns: string[]
  samples: Record<string, string[]>
  mappings: ImportMapping[]
  validation: ImportValidationSummary | null
  stages: string[]
  result: ImportResult | null
  error: string | null
  limitation: string | null
  preview_rows?: ImportPreviewRow[]
  accepted_formats?: {
    structured: string
    unstructured: string
  }
  security_notice?: string
}

export interface ImportHistoryItem {
  id: string
  filename: string
  format: string
  kind: ImportSourceKind
  status: ImportStatus
  created_at: string
  updated_at: string
  uploader_username: string
  row_count: number
  imported: number | null
  skipped: number | null
  failed: number | null
  warnings: number | null
  validation: ImportValidationSummary | null
}

export interface ImportHistoryResponse {
  total: number
  data: ImportHistoryItem[]
}

export interface ImportConfirmPayload {
  mappings: Record<string, string | null>
  skip_indexes: number[]
  continue_with_warnings: boolean
}

export interface ImportInvestigatorOption {
  id: string
  username: string
  role: string
  jurisdictions: string[]
}

export interface ImportEntryOptions {
  investigator_locked: boolean
  jurisdiction_locked: boolean
  default_investigator: string | null
  default_jurisdiction: string | null
  jurisdictions: string[]
  investigators: ImportInvestigatorOption[]
  crimes: string[]
}

export interface ManualImportRecord {
  fir_id?: string
  date?: string
  crime?: string
  jurisdiction?: string
  investigator?: string
  person_id?: string
  name?: string
  phone?: string
  vehicle_no?: string
  bank_account?: string
  social_id?: string
  home_city?: string
  location?: string
  risk_group?: string
  vehicle_type?: string
  registered_city?: string
  notes?: string
  custom_fields?: Array<{ key: string; value: string }>
}

export interface ManualImportPayload extends ManualImportRecord {
  records?: ManualImportRecord[]
}
