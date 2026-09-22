import { RefreshCw, Scale, TriangleAlert } from 'lucide-react'
import { useEffect } from 'react'

import {
  AdjudicationQueueTable,
  AdjudicationReviewPanel,
} from '@/components/adjudication'
import { Button, EmptyState, LinkButton, Panel, SectionHeader } from '@/components/ui'
import { useAdjudicationQueue, useAuth } from '@/hooks'
import { formatNumber } from '@/lib/format'
import { isForbidden, isUnauthorized, toErrorMessage } from '@/services'

export function AdjudicationQueuePage() {
  const { canReadGovernance, canAdjudicate } = useAuth()
  const {
    queue,
    reviews,
    total,
    selectedReviewId,
    selectReview,
    detail,
    selectedReview,
    reload,
    submitConfirm,
    submitReject,
  } = useAdjudicationQueue()

  useEffect(() => {
    const firstReview = reviews?.[0]
    if (!selectedReviewId && firstReview) {
      selectReview(firstReview.review_id)
    }
  }, [reviews, selectReview, selectedReviewId])

  if (!canReadGovernance) {
    return (
      <EmptyState
        icon={<Scale size={16} strokeWidth={1.75} />}
        title="Insufficient permissions"
        description="Your account cannot access the adjudication queue."
        actions={<LinkButton to="/">Return to dashboard</LinkButton>}
      />
    )
  }

  const loadFailed = queue.error !== null && reviews === null
  const errorMessage = queue.error ?? ''
  const unauthorized = isUnauthorized(queue.error) || /401|not authenticated/i.test(errorMessage)
  const forbidden = isForbidden(queue.error) || /403|insufficient permissions/i.test(errorMessage)

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Governance"
        title="Adjudication Queue"
        description="Review ambiguous entity resolution matches before any canonical merge is applied."
        actions={
          <Button
            size="sm"
            onClick={reload}
            disabled={queue.isLoading}
            icon={
              <Scale
                size={13}
                strokeWidth={1.75}
                className={queue.isLoading ? 'animate-pulse' : undefined}
              />
            }
          >
            {queue.isLoading ? 'Loading' : 'Reload'}
          </Button>
        }
      />

      {loadFailed ? (
        <Panel>
          <EmptyState
            icon={<TriangleAlert size={16} strokeWidth={1.75} />}
            title={
              unauthorized
                ? 'Authentication required'
                : forbidden
                  ? 'Access denied'
                  : 'Unable to load adjudication queue.'
            }
            description={queue.error ? toErrorMessage(queue.error) : undefined}
            actions={
              unauthorized ? (
                <LinkButton to="/login" variant="primary">
                  Sign in
                </LinkButton>
              ) : (
                <Button
                  onClick={reload}
                  icon={<RefreshCw size={13} strokeWidth={1.75} />}
                >
                  Retry
                </Button>
              )
            }
          />
        </Panel>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
          <Panel>
            <div className="flex items-center justify-between border-b border-line px-3 py-2 text-2xs text-ink-muted">
              <span>
                {reviews
                  ? `${formatNumber(total)} pending review(s)`
                  : 'Loading…'}
              </span>
              <Button size="sm" variant="ghost" onClick={reload}>
                <RefreshCw size={13} strokeWidth={1.75} />
              </Button>
            </div>
            <AdjudicationQueueTable
              reviews={reviews}
              isLoading={queue.isLoading}
              selectedReviewId={selectedReviewId}
              onSelect={selectReview}
            />
          </Panel>

          <Panel>
            <div className="border-b border-line px-3 py-2 text-2xs text-ink-muted">
              Review detail
            </div>
            <AdjudicationReviewPanel
              review={selectedReview}
              isLoading={detail.isLoading}
              canDecide={canAdjudicate}
              onConfirm={(reviewId, canonicalEntityId, reason) =>
                submitConfirm(reviewId, {
                  canonical_entity_id: canonicalEntityId,
                  ...(reason ? { reason } : {}),
                })
              }
              onReject={(reviewId, reason) =>
                submitReject(reviewId, reason ? { reason } : {})
              }
            />
          </Panel>
        </div>
      )}
    </div>
  )
}
