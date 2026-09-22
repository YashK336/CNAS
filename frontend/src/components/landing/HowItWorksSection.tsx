import { ChevronDown } from 'lucide-react'
import { Fragment } from 'react'

import { LandingContainer } from './LandingContainer'
import { LandingSection } from './LandingSection'
import { RevealOnScroll } from './RevealOnScroll'
import { SectionHeading } from './SectionHeading'
import type { StageVisualKind } from './StageMicroVisual'
import { StageMicroVisual } from './StageMicroVisual'

interface Stage {
  kind: StageVisualKind
  label: string
  description: string
}

const STAGES: Stage[] = [
  {
    kind: 'gather',
    label: 'Gather',
    description: 'FIRs, case notes, and other case documents are brought into one place.',
  },
  {
    kind: 'understand',
    label: 'Understand',
    description: 'CNAS reads the text and picks out the people, places, and things it mentions.',
  },
  {
    kind: 'connect',
    label: 'Connect',
    description: 'Those mentions are matched to the right record and linked into a graph.',
  },
  {
    kind: 'analyze',
    label: 'Analyze',
    description: 'The graph is examined for unusual patterns, risk, and central figures.',
  },
  {
    kind: 'verify',
    label: 'Verify',
    description: 'Every result stays traceable, so an analyst can check it before acting on it.',
  },
]

/** Thin connector between stage cards with a slow highlight sweep. */
function FlowConnector() {
  return (
    <>
      <div className="hidden w-8 shrink-0 items-center justify-center lg:flex">
        <div className="relative h-px w-full overflow-hidden bg-line-strong">
          <span className="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-accent/80 to-transparent motion-safe:animate-[cnas-flow-x_2.6s_linear_infinite]" />
        </div>
      </div>
      <div className="flex shrink-0 items-center justify-center py-1 lg:hidden">
        <ChevronDown size={16} strokeWidth={1.75} className="text-ink-faint" />
      </div>
    </>
  )
}

export function HowItWorksSection() {
  return (
    <LandingSection
      id="how-it-works"
      intensity={0.55}
      tint="bg-canvas/55"
      className="scroll-mt-20 border-b border-line/70 py-20 sm:py-24"
    >
      <LandingContainer className="relative">
        <RevealOnScroll>
          <SectionHeading
            eyebrow="How CNAS works"
            title="From scattered case files to a picture an analyst can act on"
            description="No jargon required — five steps take a stack of documents to a traceable, connected view of a case."
          />
        </RevealOnScroll>

        <div className="mt-12 flex flex-col lg:flex-row lg:items-stretch">
          {STAGES.map((stage, index) => (
            <Fragment key={stage.label}>
              <RevealOnScroll delayMs={index * 80} className="flex flex-1">
                <div className="relative flex flex-1 flex-col gap-3 rounded-2xl border border-line bg-surface px-4 py-4 transition-colors duration-300 hover:border-line-strong hover:bg-surface-raised">
                  <div className="flex items-center justify-between">
                    <StageMicroVisual kind={stage.kind} />
                    <span className="text-2xs font-semibold text-ink-faint">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-ink">{stage.label}</p>
                  <p className="text-xs leading-relaxed text-ink-muted">{stage.description}</p>
                </div>
              </RevealOnScroll>

              {index < STAGES.length - 1 ? <FlowConnector /> : null}
            </Fragment>
          ))}
        </div>
      </LandingContainer>
    </LandingSection>
  )
}
