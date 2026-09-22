import { cn } from '@/lib/cn'

export interface SkeletonProps {
  className?: string
}

/** Placeholder block shown while a section's request is in flight. */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <span
      aria-hidden
      className={cn(
        'block animate-pulse rounded-sm bg-surface-active',
        className,
      )}
    />
  )
}
