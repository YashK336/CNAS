import type { HTMLAttributes, PointerEvent as ReactPointerEvent } from 'react'
import { useRef } from 'react'

import { cn } from '@/lib/cn'

/**
 * Card shell with a cursor-tracked spotlight, driven entirely by two CSS
 * custom properties written directly to the DOM node (no re-render per
 * pointer move). Pairs with `group-hover:` utilities on children for the
 * icon/border/lift response. Reusable beyond the landing page.
 */
export function SpotlightCard({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  const ref = useRef<HTMLDivElement>(null)

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    el.style.setProperty('--spot-x', `${event.clientX - rect.left}px`)
    el.style.setProperty('--spot-y', `${event.clientY - rect.top}px`)
  }

  return (
    <div
      ref={ref}
      onPointerMove={handlePointerMove}
      className={cn(
        'group relative overflow-hidden rounded-2xl border border-line bg-surface transition-[border-color,background-color,transform,box-shadow] duration-300 ease-out hover:-translate-y-1 hover:border-line-strong hover:bg-surface-raised hover:shadow-[0_18px_40px_-24px_rgba(0,0,0,0.65)]',
        className,
      )}
      {...rest}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background:
            'radial-gradient(240px circle at var(--spot-x, 50%) var(--spot-y, 0%), rgba(75,141,248,0.10), transparent 72%)',
        }}
      />
      <div className="relative">{children}</div>
    </div>
  )
}
