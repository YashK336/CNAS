import { http } from './api'
import type { RequestOptions } from './api'
import type {
  SavedInvestigation,
  SavedInvestigationInput,
  SavedInvestigationListResponse,
  SavedInvestigationUpdateInput,
} from '@/types'

export function getInvestigations(
  options?: RequestOptions,
): Promise<SavedInvestigationListResponse> {
  return http.get<SavedInvestigationListResponse>('/investigations', options)
}

export function getInvestigation(
  investigationId: string,
  options?: RequestOptions,
): Promise<SavedInvestigation> {
  return http.get<SavedInvestigation>(
    `/investigations/${encodeURIComponent(investigationId)}`,
    options,
  )
}

export function createInvestigation(
  payload: SavedInvestigationInput,
  options?: RequestOptions,
): Promise<SavedInvestigation> {
  return http.post<SavedInvestigation>('/investigations', payload, options)
}

export function updateInvestigation(
  investigationId: string,
  payload: SavedInvestigationUpdateInput,
  options?: RequestOptions,
): Promise<SavedInvestigation> {
  return http.put<SavedInvestigation>(
    `/investigations/${encodeURIComponent(investigationId)}`,
    payload,
    options,
  )
}
