import { ArrowRight, FileSearch, GitBranch, ShieldCheck } from 'lucide-react'

import { CtaLink } from './CtaLink'
import { ctaButtonClass } from './ctaStyles'
import { LandingContainer } from './LandingContainer'
import { LandingSection } from './LandingSection'
import { RevealOnScroll } from './RevealOnScroll'
import { TransformationVisual } from './TransformationVisual'

const TRUST_POINTS = [
  { icon: FileSearch, label: 'FIR & document ingestion' },
  { icon: GitBranch, label: 'Entity resolution' },
  { icon: ShieldCheck, label: 'Explainable findings' },
]

export function HeroSection() {
  return (
    <LandingSection
      intensity={1}
      tint="bg-transparent"
      className="overflow-hidden border-b border-line/70"
    >
      {/* The hero shows the ambient backdrop at its brightest — only a
          faint fade at the very bottom, easing into the next section's
          tint, so the handoff reads as continuous rather than a seam. */}
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-b from-canvas/5 via-transparent to-canvas/60"
      />

      <LandingContainer className="relative py-20 sm:py-28 lg:py-32">
        <div className="grid items-center gap-14 lg:grid-cols-[1.15fr_0.85fr] lg:gap-10">
          <div>
            <RevealOnScroll>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-line-strong bg-surface-raised/80 px-3 py-1 text-2xs font-medium tracking-wide text-ink-muted">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-accent motion-safe:animate-[cnas-pulse-soft_2.6s_ease-in-out_infinite]" />
                </span>
                Investigative intelligence platform
              </div>
            </RevealOnScroll>

            <RevealOnScroll delayMs={80}>
              <h1 className="text-4xl leading-[1.08] font-semibold tracking-tight text-ink sm:text-5xl lg:text-[3.4rem]">
                Turn fragmented investigative data into{' '}
                <span className="text-accent">connected intelligence.</span>
              </h1>
            </RevealOnScroll>

            <RevealOnScroll delayMs={150}>
              <p className="mt-6 max-w-xl text-base leading-relaxed text-ink-muted sm:text-lg">
                CNAS gathers FIRs and case documents, works out who and what
                they mention, and connects those mentions into one graph —
                so an analyst sees the network behind a case, not just a
                stack of separate files.
              </p>
            </RevealOnScroll>

            <RevealOnScroll delayMs={220}>
              <div className="mt-9 flex flex-wrap items-center gap-3">
                <CtaLink to="/login">
                  Enter the Investigation Platform
                  <ArrowRight size={15} strokeWidth={2} />
                </CtaLink>
                <a href="#how-it-works" className={ctaButtonClass('secondary')}>
                  Explore How It Works
                </a>
              </div>
            </RevealOnScroll>

            <RevealOnScroll delayMs={280}>
              <dl className="mt-12 flex flex-wrap gap-x-8 gap-y-4">
                {TRUST_POINTS.map(({ icon: Icon, label }) => (
                  <div key={label} className="flex items-center gap-2">
                    <Icon size={15} strokeWidth={1.75} className="text-accent" />
                    <dt className="text-xs font-medium text-ink-muted">{label}</dt>
                  </div>
                ))}
              </dl>
            </RevealOnScroll>
          </div>

          <RevealOnScroll delayMs={150} distance={20} scale className="relative">
            <TransformationVisual />
          </RevealOnScroll>
        </div>
      </LandingContainer>
    </LandingSection>
  )
}
