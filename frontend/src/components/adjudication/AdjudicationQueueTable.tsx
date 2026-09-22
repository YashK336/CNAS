import { Badge, EmptyState, Skeleton } from '@/components/ui'
import { formatDateTime, formatNumber, formatText } from '@/lib/format'
import type { EntityResolutionReview } from '@/types'
import { cn } from '@/lib/cn'

export interface AdjudicationQueueTableProps {
  reviews: EntityResolutionReview[] | null
  isLoading: boolean
  selectedReviewId: string | null
  onSelect: (reviewId: string) => void
}

export function AdjudicationQueueTable({
  reviews,
  isLoading,
  selectedReviewId,
  onSelect,
}: AdjudicationQueueTableProps) {
  if (isLoading && !reviews) {
    return (
      <div className="space-y-2 p-3">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    )
  }

  if (!reviews || reviews.length === 0) {
    return (
      <EmptyState
        className="m-3"
        title="No pending adjudication reviews."
        description="Ambiguous entity resolution matches will appear here for human review."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-xs">
        <thead className="border-b border-line bg-surface-raised text-2xs tracking-widest text-ink-faint uppercase">
          <tr>
            <th className="px-3 py-2 font-semibold">Candidate</th>
            <th className="px-3 py-2 font-semibold">Method</th>
            <th className="px-3 py-2 font-semibold">Score</th>
            <th className="px-3 py-2 font-semibold">Proposed IDs</th>
            <th className="px-3 py-2 font-semibold">Jurisdiction</th>
            <th className="px-3 py-2 font-semibold">Queued</th>
          </tr>
        </thead>
        <tbody>
          {reviews.map((review) => (
            <tr
              key={review.review_id}
              onClick={() => onSelect(review.review_id)}
              className={cn(
                'cursor-pointer border-b border-line/70 hover:bg-surface-hover',
                selectedReviewId === review.review_id && 'bg-surface-raised',
              )}
            >
              <td className="px-3 py-2.5 align-top">
                <div className="font-medium text-ink">{formatText(review.candidate_value)}</div>
                <div className="mt-1 flex flex-wrap gap-1">
                  <Badge tone="neutral">{review.entity_type}</Badge>
                  <Badge tone="medium">pending</Badge>
                </div>
              </td>
              <td className="px-3 py-2.5 align-top font-mono text-2xs text-ink-muted">
                {review.matching_method}
              </td>
              <td className="px-3 py-2.5 align-top">
                {review.match_score !== null ? review.match_score.toFixed(1) : '—'}
              </td>
              <td className="px-3 py-2.5 align-top">
                <div className="flex flex-wrap gap-1">
                  {review.proposed_entity_ids.slice(0, 3).map((entityId) => (
                    <Badge key={entityId} tone="neutral" mono>
                      {entityId}
                    </Badge>
                  ))}
                  {review.proposed_entity_ids.length > 3 ? (
                    <Badge tone="neutral">
                      +{formatNumber(review.proposed_entity_ids.length - 3)}
                    </Badge>
                  ) : null}
                </div>
              </td>
              <td className="px-3 py-2.5 align-top">
                {review.jurisdiction ? (
                  <Badge tone="accent">{review.jurisdiction}</Badge>
                ) : (
                  '—'
                )}
              </td>
              <td className="px-3 py-2.5 align-top text-ink-muted">
                {formatDateTime(review.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
