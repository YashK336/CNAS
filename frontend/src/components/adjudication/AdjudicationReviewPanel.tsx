import { useMemo, useState } from 'react'
import { Check, X } from 'lucide-react'

import { Badge, Button, EmptyState, Skeleton } from '@/components/ui'
import { formatDateTime, formatText } from '@/lib/format'
import { toErrorMessage } from '@/services'
import type { EntityResolutionReview } from '@/types'

export interface AdjudicationReviewPanelProps {
  review: EntityResolutionReview | null
  isLoading: boolean
  canDecide: boolean
  onConfirm: (reviewId: string, canonicalEntityId: string, reason?: string) => Promise<void>
  onReject: (reviewId: string, reason?: string) => Promise<void>
}

export function AdjudicationReviewPanel({
  review,
  isLoading,
  canDecide,
  onConfirm,
  onReject,
}: AdjudicationReviewPanelProps) {
  const [selectedEntityId, setSelectedEntityId] = useState<string>('')
  const [reason, setReason] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const scoreRows = useMemo(() => {
    if (!review) return []
    return Object.entries(review.candidate_scores).sort((a, b) => b[1] - a[1])
  }, [review])

  if (isLoading && !review) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-24 w-full" />
      </div>
    )
  }

  if (!review) {
    return (
      <EmptyState
        className="m-3"
        title="Select a review"
        description="Choose a pending item from the queue to compare candidates and adjudicate."
      />
    )
  }

  const activeEntityId = selectedEntityId || review.proposed_entity_ids[0] || ''
  const reviewId = review.review_id

  async function handleConfirm() {
    if (!activeEntityId) return
    setIsSubmitting(true)
    setActionError(null)
    try {
      await onConfirm(reviewId, activeEntityId, reason.trim() || undefined)
      setReason('')
    } catch (error) {
      setActionError(toErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleReject() {
    setIsSubmitting(true)
    setActionError(null)
    try {
      await onReject(reviewId, reason.trim() || undefined)
      setReason('')
    } catch (error) {
      setActionError(toErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="text-2xs tracking-widest text-ink-faint uppercase">Candidate</p>
        <h3 className="mt-1 text-sm font-semibold text-ink">
          {formatText(review.candidate_value)}
        </h3>
        <div className="mt-2 flex flex-wrap gap-1">
          <Badge tone="neutral">{review.entity_type}</Badge>
          <Badge tone="medium">{review.status}</Badge>
          {review.jurisdiction ? <Badge tone="accent">{review.jurisdiction}</Badge> : null}
        </div>
      </div>

      <div className="rounded-sm border border-line bg-surface-raised p-3">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Ambiguity
        </p>
        <p className="mt-1 text-xs text-ink-muted">{review.ambiguity_reason}</p>
        <p className="mt-2 font-mono text-2xs text-ink-faint">
          method: {review.matching_method}
          {review.match_score !== null
            ? ` · score ${review.match_score.toFixed(1)}`
            : ''}
        </p>
      </div>

      <div>
        <p className="mb-2 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Proposed canonical IDs
        </p>
        <div className="space-y-2">
          {review.proposed_entity_ids.map((entityId) => (
            <label
              key={entityId}
              className="flex cursor-pointer items-center gap-2 rounded-sm border border-line px-3 py-2 hover:bg-surface-hover"
            >
              <input
                type="radio"
                name="canonical-entity"
                value={entityId}
                checked={activeEntityId === entityId}
                onChange={() => setSelectedEntityId(entityId)}
                disabled={!canDecide || isSubmitting}
              />
              <span className="font-mono text-xs text-ink">{entityId}</span>
              {scoreRows.find(([id]) => id === entityId) ? (
                <Badge tone="neutral">{scoreRows.find(([id]) => id === entityId)![1].toFixed(1)}</Badge>
              ) : null}
            </label>
          ))}
        </div>
      </div>

      {Object.keys(review.corroborating_evidence).length > 0 ? (
        <div>
          <p className="mb-2 text-2xs font-semibold tracking-widest text-ink-faint uppercase">
            Corroborating evidence
          </p>
          <dl className="space-y-1 rounded-sm border border-line bg-surface-raised p-3 text-2xs">
            {Object.entries(review.corroborating_evidence).map(([key, value]) => (
              <div key={key} className="grid grid-cols-[120px_1fr] gap-2">
                <dt className="text-ink-faint">{key}</dt>
                <dd className="font-mono text-ink-muted">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      {canDecide ? (
        <div className="space-y-2">
          <label className="block text-2xs text-ink-faint" htmlFor="decision-reason">
            Decision reason (optional)
          </label>
          <textarea
            id="decision-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={2}
            className="w-full rounded-sm border border-line bg-canvas px-2 py-1.5 text-xs text-ink"
            disabled={isSubmitting}
          />
          {actionError ? (
            <p className="text-2xs text-danger">{actionError}</p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="primary"
              disabled={isSubmitting || !activeEntityId}
              onClick={() => void handleConfirm()}
              icon={<Check size={13} strokeWidth={1.75} />}
            >
              Confirm merge
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={isSubmitting}
              onClick={() => void handleReject()}
              icon={<X size={13} strokeWidth={1.75} />}
            >
              Reject
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-2xs text-ink-muted">
          Your role can view adjudication items but cannot confirm or reject merges.
        </p>
      )}

      <p className="font-mono text-2xs text-ink-faint">
        review {review.review_id} · queued {formatDateTime(review.created_at)}
      </p>
    </div>
  )
}
