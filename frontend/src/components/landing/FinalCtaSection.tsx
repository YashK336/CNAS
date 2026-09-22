import { ArrowRight } from 'lucide-react'

import { CtaLink } from './CtaLink'
import { LandingContainer } from './LandingContainer'
import { LandingSection } from './LandingSection'
import { RevealOnScroll } from './RevealOnScroll'

export function FinalCtaSection() {
  return (
    <LandingSection
      intensity={0.95}
      tint="bg-transparent"
      className="overflow-hidden border-b border-line/70 py-20 sm:py-24"
    >
      {/* Bookends the hero's energy — the backdrop is bright again here,
          with just enough tint at the edges to keep the heading legible. */}
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-b from-canvas/45 via-transparent to-canvas/45"
      />

      <LandingContainer className="relative flex flex-col items-center text-center">
        <RevealOnScroll className="flex flex-col items-center">
          <h2 className="max-w-xl text-2xl leading-tight font-semibold tracking-tight text-ink sm:text-3xl">
            Your case files already contain the connections. Go find them.
          </h2>
          <p className="mt-3 max-w-lg text-sm leading-relaxed text-ink-muted sm:text-base">
            Sign in to your analyst workspace and start from the network
            explorer, the case list, or a single FIR.
          </p>
          <CtaLink to="/login" className="mt-8">
            Enter the Investigation Platform
            <ArrowRight size={15} strokeWidth={2} />
          </CtaLink>
        </RevealOnScroll>
      </LandingContainer>
    </LandingSection>
  )
}
