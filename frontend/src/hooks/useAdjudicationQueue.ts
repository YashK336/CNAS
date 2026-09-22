import { useCallback, useState } from 'react'

import {
  confirmReview,
  getPendingReviews,
  getReviewDetail,
  rejectReview,
} from '@/services'
import type {
  AdjudicationReviewListResponse,
  ConfirmReviewInput,
  EntityResolutionReview,
  RejectReviewInput,
} from '@/types'
import { useAsyncResource } from './useAsyncResource'

export function useAdjudicationQueue() {
  const queue = useAsyncResource<AdjudicationReviewListResponse>(
    (options) => getPendingReviews(options),
    [],
  )

  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null)
  const detail = useAsyncResource<EntityResolutionReview | null>(
    async (options) => {
      if (!selectedReviewId) {
        return null
      }
      return getReviewDetail(selectedReviewId, options)
    },
    [selectedReviewId],
  )

  const selectReview = useCallback((reviewId: string | null) => {
    setSelectedReviewId(reviewId)
  }, [])

  const reload = useCallback(() => {
    void queue.refetch()
    if (selectedReviewId) {
      void detail.refetch()
    }
  }, [queue, detail, selectedReviewId])

  const submitConfirm = useCallback(
    async (reviewId: string, payload: ConfirmReviewInput) => {
      await confirmReview(reviewId, payload)
      reload()
    },
    [reload],
  )

  const submitReject = useCallback(
    async (reviewId: string, payload: RejectReviewInput) => {
      await rejectReview(reviewId, payload)
      reload()
    },
    [reload],
  )

  return {
    queue,
    reviews: queue.data?.reviews ?? null,
    total: queue.data?.total ?? 0,
    selectedReviewId,
    selectReview,
    detail,
    selectedReview: detail.data ?? null,
    reload,
    submitConfirm,
    submitReject,
  }
}
