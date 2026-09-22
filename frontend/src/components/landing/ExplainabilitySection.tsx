import { AlertTriangle, Database, GaugeCircle, Target, Workflow } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Badge } from '@/components/ui'
import { LandingContainer } from './LandingContainer'
import { LandingSection } from './LandingSection'
import { RevealOnScroll } from './RevealOnScroll'
import { SectionHeading } from './SectionHeading'

interface ExplainabilityItem {
  icon: LucideIcon
  title: string
  description: string
  sample: string
}

const ITEMS: ExplainabilityItem[] = [
  {
    icon: Target,
    title: 'Claim',
    description:
      'What is being asserted — a proposed relationship, entity match, or risk signal surfaced by the graph.',
    sample: 'P104 is linked to P217',
  },
  {
    icon: Database,
    title: 'Evidence',
    description:
      'The source record, extracted span, and any corroborating references the claim is built from.',
    sample: 'FIR-2024-0182, call log · 3 calls in 48h',
  },
  {
    icon: Workflow,
    title: 'Method',
    description:
      'How the claim was produced — exact identifier match, fuzzy name resolution, regex extraction, or NER.',
    sample: 'exact_phone match',
  },
  {
    icon: GaugeCircle,
    title: 'Confidence',
    description:
      'A numeric score reflecting the resolution method\u2019s certainty, carried on every relationship in the graph.',
    sample: 'conf 0.94',
  },
  {
    icon: AlertTriangle,
    title: 'Limits',
    description:
      'Ambiguous or conflicting matches are never merged automatically — they are queued for analyst adjudication instead.',
    sample: 'No conflicting matches on this identifier',
  },
]

/** A concrete, illustrative finding rendered with all five fields filled in. */
function SampleFindingCard() {
  return (
    <div className="rounded-2xl border border-line-strong bg-surface-raised/80 p-5 shadow-[0_24px_60px_-32px_rgba(0,0,0,0.7)] backdrop-blur-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
          Sample finding
        </p>
        <span className="rounded-sm border border-line-strong bg-surface px-1.5 py-0.5 text-2xs text-ink-faint">
          Illustrative
        </span>
      </div>

      <p className="mt-4 text-sm font-semibold text-ink">
        &ldquo;P104 is linked to P217&rdquo;
      </p>

      <dl className="mt-4 space-y-3 border-t border-line/70 pt-4">
        {ITEMS.map((item) => (
          <div key={item.title} className="flex items-start justify-between gap-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-ink-muted">
              <item.icon size={13} strokeWidth={1.75} className="text-accent" />
              {item.title}
            </dt>
            <dd className="text-right font-mono text-2xs text-ink">{item.sample}</dd>
          </div>
        ))}
      </dl>

      <p className="mt-4 border-t border-line/70 pt-3 text-2xs leading-relaxed text-ink-faint">
        A constructed example for illustration — not an actual case record.
      </p>
    </div>
  )
}

export function ExplainabilitySection() {
  return (
    <LandingSection
      id="explainability"
      intensity={0.45}
      tint="bg-canvas/62"
      className="scroll-mt-20 border-b border-line/70 py-20 sm:py-24"
    >
      <LandingContainer className="relative">
        <RevealOnScroll>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <SectionHeading
              eyebrow="Explainability"
              title="Every finding answers five questions"
              description="CNAS is built so an analyst can interrogate a result, not just trust it. Findings carry their reasoning — and their limits — with them."
            />
            <Badge tone="accent" className="shrink-0">
              No unexplained edges
            </Badge>
          </div>
        </RevealOnScroll>

        <div className="mt-12 grid gap-10 lg:grid-cols-[0.95fr_1.05fr] lg:gap-14">
          <ol className="relative space-y-8">
            <div
              aria-hidden
              className="absolute top-4 bottom-4 left-[19px] w-px bg-line-strong"
            />
            {ITEMS.map((item, index) => (
              <li key={item.title} className="relative pl-0">
                <RevealOnScroll delayMs={index * 70} className="flex gap-5">
                  <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-line-strong bg-surface text-accent transition-colors duration-300">
                    <item.icon size={16} strokeWidth={1.75} />
                  </span>
                  <div className="pt-1.5">
                    <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">
                      {item.description}
                    </p>
                  </div>
                </RevealOnScroll>
              </li>
            ))}
          </ol>

          <RevealOnScroll delayMs={120} distance={20}>
            <SampleFindingCard />
          </RevealOnScroll>
        </div>
      </LandingContainer>
    </LandingSection>
  )
}
