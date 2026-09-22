import type { LinkProps } from 'react-router-dom'

import { cn } from '@/lib/cn'
import { ctaButtonClass } from './ctaStyles'
import type { CtaVariant } from './ctaStyles'
import { TransitionLink } from './TransitionLink'

export interface CtaLinkProps extends LinkProps {
  variant?: CtaVariant
}

/** Premium CTA button that also performs a route-fade transition. */
export function CtaLink({ variant = 'primary', className, ...rest }: CtaLinkProps) {
  return <TransitionLink className={cn(ctaButtonClass(variant), className)} {...rest} />
}
