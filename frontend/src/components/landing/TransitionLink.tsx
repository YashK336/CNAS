import type { MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { LinkProps } from 'react-router-dom'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'

const EXIT_CLASS = 'cnas-route-exit'
const EXIT_DURATION_MS = 170

function isPlainLeftClick(event: MouseEvent<HTMLAnchorElement>): boolean {
  return (
    event.button === 0 &&
    !event.metaKey &&
    !event.altKey &&
    !event.ctrlKey &&
    !event.shiftKey
  )
}

export type TransitionLinkProps = LinkProps

/**
 * `Link` wrapper that fades the current view out before committing the
 * route change, so leaving the public landing page for `/login` reads as
 * one continuous motion rather than a hard cut. Falls back to an ordinary
 * navigation under reduced motion or for anything but a plain left click
 * (new tab, modifier-clicks, etc. are left entirely to the browser).
 */
export function TransitionLink({ to, onClick, ...rest }: TransitionLinkProps) {
  const navigate = useNavigate()
  const prefersReducedMotion = usePrefersReducedMotion()

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event)
    if (event.defaultPrevented) return
    if (!isPlainLeftClick(event)) return
    if (prefersReducedMotion) return

    const root = document.getElementById('root')
    if (!root) return

    event.preventDefault()
    root.classList.add(EXIT_CLASS)
    window.setTimeout(() => {
      navigate(to)
      // Wait two painted frames so the destination route has actually
      // mounted before we fade back in — otherwise this can reveal a
      // flash of the outgoing page instead of the new one.
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          root.classList.remove(EXIT_CLASS)
        })
      })
    }, EXIT_DURATION_MS)
  }

  return <Link to={to} onClick={handleClick} {...rest} />
}
