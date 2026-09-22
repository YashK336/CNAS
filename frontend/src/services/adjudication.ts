import { http } from './api'
import type { RequestOptions } from './api'
import type {
  AdjudicationReviewListResponse,
  ConfirmReviewInput,
  EntityResolutionReview,
  RejectReviewInput,
} from '@/types'

export function getPendingReviews(
  options?: RequestOptions,
): Promise<AdjudicationReviewListResponse> {
  return http.get<AdjudicationReviewListResponse>('/adjudication/reviews', options)
}

export function getReviewDetail(
  reviewId: string,
  options?: RequestOptions,
): Promise<EntityResolutionReview> {
  return http.get<EntityResolutionReview>(
    `/adjudication/reviews/${encodeURIComponent(reviewId)}`,
    options,
  )
}

export function confirmReview(
  reviewId: string,
  payload: ConfirmReviewInput,
  options?: RequestOptions,
): Promise<EntityResolutionReview> {
  return http.post<EntityResolutionReview>(
    `/adjudication/reviews/${encodeURIComponent(reviewId)}/confirm`,
    payload,
    options,
  )
}

export function rejectReview(
  reviewId: string,
  payload: RejectReviewInput,
  options?: RequestOptions,
): Promise<EntityResolutionReview> {
  return http.post<EntityResolutionReview>(
    `/adjudication/reviews/${encodeURIComponent(reviewId)}/reject`,
    payload,
    options,
  )
}
