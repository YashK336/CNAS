import { cn } from '@/lib/cn'
import type { ClassValue } from '@/lib/cn'

export type CtaVariant = 'primary' | 'secondary'

const BASE_CLASS =
  'group/cta relative isolate inline-flex h-11 select-none items-center justify-center gap-2 overflow-hidden rounded-[10px] px-5 text-sm font-semibold whitespace-nowrap transition-[transform,box-shadow,background-color,border-color,opacity] duration-200 ease-out will-change-transform hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:translate-y-0 disabled:opacity-45 disabled:shadow-none'

const VARIANT_CLASS: Record<CtaVariant, string> = {
  // Subtle top-to-bottom depth gradient (not flat, not neon) with a
  // one-shot diagonal light sweep on hover and a soft accent glow — no
  // permanent glow at rest, per the "restrained" visual system.
  primary:
    'border border-accent/60 bg-[linear-gradient(180deg,#5c99f9_0%,#3f79e0_100%)] text-canvas shadow-[0_1px_0_rgba(255,255,255,0.18)_inset] hover:shadow-[0_0_0_1px_rgba(75,141,248,0.5),0_10px_28px_-10px_rgba(75,141,248,0.55)] before:absolute before:inset-0 before:-translate-x-full before:bg-[linear-gradient(115deg,transparent_35%,rgba(255,255,255,0.30)_50%,transparent_65%)] before:transition-transform before:duration-700 before:ease-out hover:before:translate-x-full',
  secondary:
    'border border-line-strong bg-surface-raised/60 text-ink backdrop-blur-sm hover:border-accent/40 hover:bg-surface-hover',
}

/** Shared between `CtaLink` and any plain anchor CTA (e.g. in-page scroll links). */
export function ctaButtonClass(
  variant: CtaVariant = 'primary',
  className?: ClassValue,
): string {
  return cn(BASE_CLASS, VARIANT_CLASS[variant], className)
}
