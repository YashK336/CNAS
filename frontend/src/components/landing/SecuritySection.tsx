import { History, KeyRound, Layers, MapPinned, ShieldAlert, UserCog } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Disclosure } from '@/components/ui'
import { LandingContainer } from './LandingContainer'
import { LandingSection } from './LandingSection'
import { RevealOnScroll } from './RevealOnScroll'
import { SectionHeading } from './SectionHeading'

interface TrustPoint {
  icon: LucideIcon
  title: string
  summary: string
  detail: string
}

const TRUST_POINTS: TrustPoint[] = [
  {
    icon: KeyRound,
    title: 'Authentication',
    summary: 'No case data is reachable without signing in — there is no anonymous view.',
    detail:
      'Access requires a signed-in session issued at login. Sessions expire and must be renewed by signing in again; there is no standing anonymous or public route into case data.',
  },
  {
    icon: UserCog,
    title: 'Role-based access',
    summary: 'What an analyst can see and change is scoped to their assigned role.',
    detail:
      'Roles gate access at the API layer, not only in the interface — for example, read access to investigations differs from the write access needed to create or adjudicate them.',
  },
  {
    icon: MapPinned,
    title: 'Jurisdiction-aware access',
    summary: 'Connections that cross jurisdictions stay visible only where they should.',
    detail:
      'Investigation and adjudication authorization checks account for jurisdiction, so a case spanning multiple jurisdictions does not become visible to everyone on either side by default.',
  },
  {
    icon: History,
    title: 'Auditability',
    summary: 'Adjudication and governance actions leave a record of who did what, and when.',
    detail:
      'Decisions made while resolving ambiguous entity matches, along with other governance actions, are written to an audit log that analysts with governance access can review.',
  },
  {
    icon: ShieldAlert,
    title: 'Fail-closed by default',
    summary: 'When a permission is ambiguous, CNAS denies access rather than assuming it.',
    detail:
      'Authorization checks are written to deny by default; a request has to match an explicit allow rule to proceed, rather than being let through because nothing explicitly blocked it.',
  },
  {
    icon: Layers,
    title: 'Evidence & provenance',
    summary: 'Every relationship in the graph carries its source back to the original record.',
    detail:
      'Extraction method, source reference, and confidence score travel with every relationship — the same provenance model used throughout the explainability section above.',
  },
]

export function SecuritySection() {
  return (
    <LandingSection
      id="security"
      intensity={0.28}
      tint="bg-canvas/78"
      className="scroll-mt-20 border-b border-line/70 py-20 sm:py-24"
    >
      <LandingContainer className="relative">
        <RevealOnScroll>
          <SectionHeading
            eyebrow="Security & trust"
            title="Access is scoped, denied by default, and left a trail"
            description="A plain-language summary of how CNAS governs who can see and change what. Open any row for the underlying detail."
          />
        </RevealOnScroll>

        <div className="mt-12 grid gap-3 lg:grid-cols-2">
          {TRUST_POINTS.map((point, index) => (
            <RevealOnScroll key={point.title} delayMs={(index % 2) * 80}>
              <Disclosure
                title={
                  <span className="flex items-center gap-2.5">
                    <point.icon size={15} strokeWidth={1.75} className="text-accent" />
                    {point.title}
                  </span>
                }
                subtitle={point.summary}
              >
                {point.detail}
              </Disclosure>
            </RevealOnScroll>
          ))}
        </div>

        <RevealOnScroll delayMs={120}>
          <p className="mt-8 max-w-2xl text-2xs leading-relaxed text-ink-faint">
            This section describes how CNAS is built to govern access today. It is not a
            claim of any third-party security certification or compliance attestation.
          </p>
        </RevealOnScroll>
      </LandingContainer>
    </LandingSection>
  )
}
