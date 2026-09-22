import { BrandMark } from '@/components/layout/BrandMark'
import { LandingContainer } from './LandingContainer'
import { TransitionLink } from './TransitionLink'

const FOOTER_LINKS = [
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Capabilities', href: '#capabilities' },
  { label: 'Security', href: '#security' },
  { label: 'Methodology', href: '#methodology' },
]

export function LandingFooter() {
  return (
    <footer id="about" className="relative scroll-mt-20 bg-canvas/70 py-10">
      <LandingContainer className="relative flex flex-col gap-6 border-t border-line/70 pt-8 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-sm">
          <div className="flex items-center gap-2">
            <BrandMark size={20} />
            <span className="text-sm font-semibold tracking-[0.14em] text-ink">
              CNAS
            </span>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-ink-faint">
            Criminal Network Analysis System — an analyst workstation for
            entity resolution, graph analytics, and evidence-linked
            investigative findings.
          </p>
        </div>

        <nav className="flex flex-wrap gap-x-6 gap-y-2">
          {FOOTER_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-xs font-medium text-ink-muted transition-colors hover:text-ink"
            >
              {link.label}
            </a>
          ))}
          <TransitionLink
            to="/login"
            className="text-xs font-medium text-ink-muted transition-colors hover:text-ink"
          >
            Sign In
          </TransitionLink>
        </nav>
      </LandingContainer>

      <LandingContainer className="mt-6">
        <p className="text-2xs text-ink-faint">
          Internal analyst tooling. Not a public data source.
        </p>
      </LandingContainer>
    </footer>
  )
}
