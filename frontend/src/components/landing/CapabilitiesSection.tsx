import {
  AlertTriangle,
  FileSearch,
  Gauge,
  GitBranch,
  Globe2,
  Layers,
  ShieldQuestion,
  UsersRound,
  Waypoints,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { CapabilityVisual } from './CapabilityVisual'
import type { CapabilityVisualKind } from './CapabilityVisual'
import { LandingContainer } from './LandingContainer'
import { LandingSection } from './LandingSection'
import { RevealOnScroll } from './RevealOnScroll'
import { SectionHeading } from './SectionHeading'
import { SpotlightCard } from './SpotlightCard'

interface Capability {
  icon: LucideIcon
  title: string
  description: string
  visual: CapabilityVisualKind
  /** Larger bento cell — reserves room to show the visual at a bigger size. */
  featured?: boolean
}

const CAPABILITIES: Capability[] = [
  {
    icon: Waypoints,
    title: 'Criminal Network Analysis',
    description:
      'Explore multi-hop relationships between people, vehicles, accounts, and locations in an interactive graph explorer.',
    visual: 'network',
    featured: true,
  },
  {
    icon: GitBranch,
    title: 'Entity Resolution',
    description:
      'Exact-identifier and fuzzy-name matching link extracted mentions to canonical entities. Ambiguous matches route to human adjudication rather than merging silently.',
    visual: 'resolution',
  },
  {
    icon: FileSearch,
    title: 'FIR Intelligence',
    description:
      'Parse FIR case narratives with regex and NER to surface phones, vehicles, accounts, and named entities directly from unstructured text.',
    visual: 'fir',
  },
  {
    icon: Gauge,
    title: 'Risk Analysis',
    description:
      'Centrality and propagation-based scoring highlight higher-risk individuals alongside the evidence that supports the score.',
    visual: 'risk',
  },
  {
    icon: AlertTriangle,
    title: 'Anomaly Detection',
    description:
      'Flag statistical outliers in call, transaction, and association patterns so analysts can prioritise review.',
    visual: 'anomaly',
  },
  {
    icon: Layers,
    title: 'Evidence & Provenance',
    description:
      'Every relationship carries a source reference, extraction method, confidence score, and ingestion timestamp back to origin.',
    visual: 'evidence',
    featured: true,
  },
  {
    icon: Globe2,
    title: 'Cross-jurisdiction Analysis',
    description:
      'Cases and reviews carry a jurisdiction tag, so cross-border patterns stay visible to the people cleared to see them.',
    visual: 'jurisdiction',
  },
  {
    icon: ShieldQuestion,
    title: 'Human Adjudication',
    description:
      'Ambiguous entity matches are queued for review rather than merged automatically — a person makes the final call.',
    visual: 'adjudication',
  },
  {
    icon: UsersRound,
    title: 'Investigator Collaboration',
    description:
      'Shared investigations, saved views, and an audit trail let a team pick up a case exactly where a colleague left it.',
    visual: 'collaboration',
    featured: true,
  },
]

export function CapabilitiesSection() {
  return (
    <LandingSection
      id="capabilities"
      intensity={0.55}
      tint="bg-canvas/58"
      className="scroll-mt-20 border-b border-line/70 py-20 sm:py-24"
    >
      <LandingContainer className="relative">
        <RevealOnScroll>
          <SectionHeading
            eyebrow="Capabilities"
            title="Built for the questions an investigation actually asks"
            description="Each module reads from the same resolved graph, so a lead found in one view stays consistent everywhere else."
          />
        </RevealOnScroll>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((capability, index) => (
            <RevealOnScroll
              key={capability.title}
              delayMs={(index % 3) * 70}
              className={capability.featured ? 'flex sm:col-span-2' : 'flex'}
            >
              <SpotlightCard className="flex h-full w-full flex-col p-5">
                <div className="flex items-start justify-between gap-3">
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-line-strong bg-surface-raised text-accent transition-[transform,border-color] duration-300 group-hover:-translate-y-0.5 group-hover:border-accent/50">
                    <capability.icon size={16} strokeWidth={1.75} />
                  </span>
                  {!capability.featured ? <CapabilityVisual kind={capability.visual} /> : null}
                </div>
                <h3 className="mt-4 text-sm font-semibold text-ink">{capability.title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-ink-muted">
                  {capability.description}
                </p>
                {capability.featured ? (
                  <div className="mt-5 flex flex-1 items-center justify-center border-t border-line/60 pt-5">
                    <CapabilityVisual kind={capability.visual} />
                  </div>
                ) : null}
              </SpotlightCard>
            </RevealOnScroll>
          ))}
        </div>
      </LandingContainer>
    </LandingSection>
  )
}
