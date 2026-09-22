/** Human adjudication queue item from `/adjudication/reviews`. */

export interface EntityResolutionReview {
  review_id: string
  candidate_value: string
  entity_type: string
  reference_entity_id: string | null
  proposed_entity_ids: string[]
  matching_method: string
  match_score: number | null
  candidate_scores: Record<string, number>
  corroborating_evidence: Record<string, unknown>
  ambiguity_reason: string
  jurisdiction: string | null
  status: 'pending' | 'confirmed' | 'rejected'
  reviewer_id: string | null
  reviewed_at: string | null
  decision_reason: string | null
  confirmed_entity_id: string | null
  created_at: string
  updated_at: string
}

export interface AdjudicationReviewListResponse {
  total: number
  reviews: EntityResolutionReview[]
}

export interface ConfirmReviewInput {
  canonical_entity_id: string
  reason?: string | null
}

export interface RejectReviewInput {
  reason?: string | null
}
