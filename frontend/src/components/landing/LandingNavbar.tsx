import { ArrowRight, Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { BrandMark } from '@/components/layout/BrandMark'
import { cn } from '@/lib/cn'
import { LandingContainer } from './LandingContainer'
import { TransitionLink } from './TransitionLink'

const NAV_LINKS = [
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Capabilities', href: '#capabilities' },
  { label: 'Security', href: '#security' },
  { label: 'Methodology', href: '#methodology' },
]

export function LandingNavbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    let ticking = false
    const handleScroll = () => {
      if (ticking) return
      ticking = true
      window.requestAnimationFrame(() => {
        setIsScrolled(window.scrollY > 8)
        ticking = false
      })
    }
    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header
      className={cn(
        'sticky top-0 z-50 border-b transition-[background-color,border-color,box-shadow] duration-300',
        isScrolled
          ? 'border-line/70 bg-canvas/85 shadow-[0_1px_0_rgba(75,141,248,0.08),0_12px_28px_-20px_rgba(0,0,0,0.6)] backdrop-blur-md'
          : 'border-transparent bg-transparent shadow-none',
      )}
    >
      <LandingContainer className="flex h-16 items-center justify-between">
        <Link
          to="/"
          className="flex shrink-0 items-center gap-2.5"
          title="CNAS — Criminal Network Analysis System"
        >
          <BrandMark size={26} />
          <span className="flex flex-col leading-none">
            <span className="text-sm font-semibold tracking-[0.16em] text-ink">
              CNAS
            </span>
            <span className="mt-0.5 hidden text-2xs tracking-wide text-ink-faint sm:block">
              Criminal Network Analysis System
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="relative py-1 text-sm font-medium text-ink-muted transition-colors after:absolute after:-bottom-0.5 after:left-0 after:h-px after:w-0 after:bg-accent after:transition-[width] after:duration-300 hover:text-ink hover:after:w-full"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden shrink-0 items-center gap-3 md:flex">
          <TransitionLink
            to="/login"
            className="inline-flex h-9 items-center gap-1.5 rounded-[10px] border border-accent/50 bg-accent/12 px-4 text-sm font-medium text-accent transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/80 hover:bg-accent/20"
          >
            Sign In
            <ArrowRight size={14} strokeWidth={1.75} />
          </TransitionLink>
        </div>

        <button
          type="button"
          onClick={() => setIsMenuOpen((open) => !open)}
          aria-expanded={isMenuOpen}
          aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
          className="inline-flex h-9 w-9 items-center justify-center rounded-sm border border-line-strong text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink md:hidden"
        >
          {isMenuOpen ? (
            <X size={17} strokeWidth={1.75} />
          ) : (
            <Menu size={17} strokeWidth={1.75} />
          )}
        </button>
      </LandingContainer>

      <div
        className={cn(
          'overflow-hidden border-b border-line/70 bg-canvas transition-[max-height] duration-300 ease-out md:hidden',
          isMenuOpen ? 'max-h-72' : 'max-h-0 border-b-0',
        )}
      >
        <LandingContainer className="flex flex-col gap-1 py-3">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setIsMenuOpen(false)}
              className="rounded-sm px-2 py-2.5 text-sm font-medium text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
            >
              {link.label}
            </a>
          ))}
          <TransitionLink
            to="/login"
            onClick={() => setIsMenuOpen(false)}
            className="mt-2 inline-flex h-9 items-center justify-center gap-1.5 rounded-[10px] border border-accent/50 bg-accent/12 text-sm font-medium text-accent"
          >
            Sign In
            <ArrowRight size={14} strokeWidth={1.75} />
          </TransitionLink>
        </LandingContainer>
      </div>
    </header>
  )
}
