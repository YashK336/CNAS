import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/cn'

/**
 * Marketing-width wrapper. Wider than the authenticated app's
 * `max-w-[1600px]` work area since landing content reads better centred
 * with generous side margins.
 */
export function LandingContainer({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('mx-auto w-full max-w-6xl px-5 sm:px-8 lg:px-10', className)}
      {...rest}
    >
      {children}
    </div>
  )
}
