/**
 * Module-level target for the shared page backdrop's "energy" — how bright
 * and active the ambient network reads. Sections nudge this via
 * `useBackdropZone` as they scroll into view; `LandingBackdrop` reads it
 * every animation frame and eases toward it, so handoffs between sections
 * feel like one continuous environment rather than a hard cut.
 *
 * A plain mutable module value (not React state) is deliberate: this only
 * feeds a canvas render loop, so there is nothing to gain from routing it
 * through a re-render.
 */
export interface BackdropState {
  target: number
}

export const backdropState: BackdropState = { target: 0.85 }

export function setBackdropIntensity(value: number): void {
  backdropState.target = Math.min(1, Math.max(0, value))
}
