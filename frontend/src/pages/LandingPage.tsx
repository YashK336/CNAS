import {
  CapabilitiesSection,
  CursorGlow,
  EntryOverlay,
  ExplainabilitySection,
  FinalCtaSection,
  HeroSection,
  HowItWorksSection,
  IntelligenceVisualizationSection,
  LandingBackdrop,
  LandingFooter,
  LandingNavbar,
  MethodologySection,
  SecuritySection,
} from '@/components/landing'

/**
 * Public marketing page shown at `/` before authentication. Rendered by
 * `RequireAuth` in place of the dashboard when the visitor has no session —
 * it deliberately does not use `AppShell`, since the sidebar/header chrome
 * assumes an authenticated analyst.
 *
 * `LandingBackdrop` is mounted once here as a single continuous ambient
 * environment fixed behind every section. Each section is a
 * `LandingSection`, which registers itself as a scroll zone and eases the
 * backdrop's energy toward its own `intensity` as it enters view — hero and
 * the final CTA stay brightest, content sections dim it, so the page never
 * goes flat black after the hero.
 */
export function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-canvas text-ink">
      <LandingBackdrop />
      <EntryOverlay />
      <CursorGlow />
      <LandingNavbar />
      <main className="relative">
        <HeroSection />
        <HowItWorksSection />
        <CapabilitiesSection />
        <IntelligenceVisualizationSection />
        <ExplainabilitySection />
        <SecuritySection />
        <MethodologySection />
        <FinalCtaSection />
      </main>
      <LandingFooter />
    </div>
  )
}
