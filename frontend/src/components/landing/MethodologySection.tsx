import { Compass, Eye, GitCommitHorizontal, Scale, UserCheck } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { LandingContainer } from './LandingContainer'
import { LandingSection } from './LandingSection'
import { RevealOnScroll } from './RevealOnScroll'
import { SectionHeading } from './SectionHeading'

interface MethodologyStep {
  icon: LucideIcon
  verb: string
  description: string
}

const STEPS: MethodologyStep[] = [
  {
    icon: Compass,
    verb: 'Discover',
    description:
      'Surface patterns worth a second look — unusual connections, repeated identifiers, risk clusters.',
  },
  {
    icon: Eye,
    verb: 'Inspect',
    description: 'Open any relationship in the graph and see exactly how it was formed.',
  },
  {
    icon: GitCommitHorizontal,
    verb: 'Trace',
    description: 'Follow a piece of evidence back to the FIR, call log, or record it came from.',
  },
  {
    icon: Scale,
    verb: 'Evaluate',
    description: 'Weigh confidence and stated limits alongside the signal itself, not instead of it.',
  },
  {
    icon: UserCheck,
    verb: 'Decide',
    description:
      'The analyst confirms, rejects, or escalates. CNAS never merges an uncertain match on its own.',
  },
]

export function MethodologySection() {
  return (
    <LandingSection
      id="methodology"
      intensity={0.32}
      tint="bg-canvas/76"
      className="scroll-mt-20 border-b border-line/70 py-20 sm:py-24"
    >
      <LandingContainer className="relative">
        <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
          <RevealOnScroll>
            <SectionHeading
              eyebrow="Methodology"
              title="An assistant for investigative judgment, not a replacement for it"
              description="CNAS narrows down what deserves attention and shows its reasoning. The analyst stays the one making the call — every step below ends with a person, not an automatic action."
            />

            <div className="mt-8 flex items-center gap-3 rounded-2xl border border-line-strong bg-surface-raised/70 px-4 py-3">
              <UserCheck size={18} strokeWidth={1.75} className="shrink-0 text-accent" />
              <p className="text-xs leading-relaxed text-ink-muted">
                Nothing in this loop resolves, merges, or closes a case without a human
                decision recorded against it.
              </p>
            </div>
          </RevealOnScroll>

          <ol className="relative space-y-6">
            <div
              aria-hidden
              className="absolute top-4 bottom-4 left-[19px] w-px bg-line-strong"
            />
            {STEPS.map((step, index) => (
              <li key={step.verb} className="relative pl-0">
                <RevealOnScroll delayMs={index * 70} className="flex gap-5">
                  <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-line-strong bg-surface text-accent transition-colors duration-300">
                    <step.icon size={16} strokeWidth={1.75} />
                  </span>
                  <div className="pt-1.5">
                    <h3 className="text-sm font-semibold text-ink">{step.verb}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">
                      {step.description}
                    </p>
                  </div>
                </RevealOnScroll>
              </li>
            ))}
          </ol>
        </div>
      </LandingContainer>
    </LandingSection>
  )
}
