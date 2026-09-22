import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '@/lib/cn'
import { ctaButtonClass } from './ctaStyles'
import type { CtaVariant } from './ctaStyles'

export interface CtaButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: CtaVariant
  icon?: ReactNode
}

/**
 * Button counterpart to `CtaLink` — same premium CTA language, for forms
 * and in-page actions where a route change is not the trigger.
 */
export function CtaButton({
  variant = 'primary',
  icon,
  className,
  children,
  type = 'button',
  ...rest
}: CtaButtonProps) {
  return (
    <button type={type} className={cn(ctaButtonClass(variant), className)} {...rest}>
      {icon}
      {children}
    </button>
  )
}
