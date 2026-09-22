import { http } from './api'
import type { RequestOptions } from './api'
import type {
  CnasField,
  ImportBatch,
  ImportConfirmPayload,
  ImportEntryOptions,
  ImportHistoryResponse,
  ImportSourceKind,
  ManualImportPayload,
} from '@/types'

const INSPECT_TIMEOUT_MS = 60_000
const CONFIRM_TIMEOUT_MS = 120_000

export function getImportFields(
  options?: RequestOptions,
): Promise<{ data: CnasField[] }> {
  return http.get<{ data: CnasField[] }>('/imports/fields', options)
}

export function getImportOptions(
  options?: RequestOptions,
): Promise<ImportEntryOptions> {
  return http.get<ImportEntryOptions>('/imports/options', options)
}

export function getImportHistory(
  options?: RequestOptions,
): Promise<ImportHistoryResponse> {
  return http.get<ImportHistoryResponse>('/imports', options)
}

export function getImport(
  importId: string,
  options?: RequestOptions,
): Promise<ImportBatch> {
  return http.get<ImportBatch>(
    `/imports/${encodeURIComponent(importId)}`,
    options,
  )
}

export function inspectImport(
  file: File,
  sourceKind: ImportSourceKind,
  jurisdiction?: string,
  options?: RequestOptions,
): Promise<ImportBatch> {
  const body = new FormData()
  body.append('file', file)
  body.append('source_kind', sourceKind)
  if (jurisdiction?.trim()) {
    body.append('jurisdiction', jurisdiction.trim())
  }
  return http.post<ImportBatch>('/imports/inspect', body, {
    timeout: INSPECT_TIMEOUT_MS,
    ...options,
  })
}

export function inspectManualImport(
  payload: ManualImportPayload,
  options?: RequestOptions,
): Promise<ImportBatch> {
  return http.post<ImportBatch>('/imports/inspect-manual', payload, {
    timeout: INSPECT_TIMEOUT_MS,
    ...options,
  })
}

export function mapImport(
  importId: string,
  mappings: Record<string, string | null>,
  options?: RequestOptions,
): Promise<ImportBatch> {
  return http.post<ImportBatch>(
    `/imports/${encodeURIComponent(importId)}/mapping`,
    { mappings },
    options,
  )
}

export function validateImport(
  importId: string,
  payload: {
    mappings?: Record<string, string | null>
    skip_indexes?: number[]
  },
  options?: RequestOptions,
): Promise<ImportBatch> {
  return http.post<ImportBatch>(
    `/imports/${encodeURIComponent(importId)}/validate`,
    payload,
    options,
  )
}

export function confirmImport(
  importId: string,
  payload: ImportConfirmPayload,
  options?: RequestOptions,
): Promise<ImportBatch> {
  return http.post<ImportBatch>(
    `/imports/${encodeURIComponent(importId)}/confirm`,
    payload,
    { timeout: CONFIRM_TIMEOUT_MS, ...options },
  )
}
