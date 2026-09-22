import { ArrowLeft, CircleAlert, KeyRound, MapPinned, ScrollText, ShieldCheck } from 'lucide-react'
import { useCallback, useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { CtaButton, CursorGlow, TransitionLink } from '@/components/landing'
import { BrandMark } from '@/components/layout/BrandMark'
import {
  LoginField,
  LoginPasswordField,
  SecureAccessVisual,
  UnlockOverlay,
} from '@/components/login'
import { useAuth } from '@/hooks/useAuth'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { isUnauthorized, toErrorMessage } from '@/services'

const TRUST_POINTS = [
  { icon: KeyRound, label: 'Authentication' },
  { icon: ShieldCheck, label: 'Role-based access' },
  { icon: MapPinned, label: 'Jurisdiction-aware access' },
  { icon: ScrollText, label: 'Audited activity' },
] as const

function ctaCopy(isSubmitting: boolean, unlocking: boolean, entering: boolean): string {
  if (unlocking && entering) return 'ENTERING CNAS'
  if (unlocking) return 'VERIFYING ACCESS...'
  if (isSubmitting) return 'AUTHENTICATING...'
  return 'SIGN IN'
}

export function LoginPage() {
  const {
    isAuthenticated,
    isInitializing,
    login,
    sessionExpiredMessage,
    clearSessionExpiredMessage,
  } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const prefersReducedMotion = usePrefersReducedMotion()
  const redirectTo =
    (location.state as { from?: string } | null)?.from ?? '/'
  const sessionExpired =
    (location.state as { sessionExpired?: boolean } | null)?.sessionExpired ===
      true || sessionExpiredMessage !== null

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [unlocking, setUnlocking] = useState(false)
  const [entering, setEntering] = useState(false)

  const sessionExpiredNotice = sessionExpired
    ? sessionExpiredMessage ?? 'Your session has expired. Sign in again to continue.'
    : null
  const displayError = error ?? sessionExpiredNotice
  const hasAuthError = displayError !== null

  const finishUnlock = useCallback(() => {
    navigate(redirectTo, { replace: true })
  }, [navigate, redirectTo])

  if (!isInitializing && isAuthenticated && !isSubmitting && !unlocking) {
    return <Navigate to={redirectTo} replace />
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    clearSessionExpiredMessage()

    void login({ username: username.trim(), password })
      .then(() => {
        if (prefersReducedMotion) {
          navigate(redirectTo, { replace: true })
          return
        }
        setUnlocking(true)
        window.setTimeout(() => setEntering(true), 220)
      })
      .catch((loginError: unknown) => {
        if (isUnauthorized(loginError)) {
          setError('Invalid username or password.')
        } else {
          setError(toErrorMessage(loginError))
        }
        setIsSubmitting(false)
      })
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-canvas text-ink">
      <CursorGlow intensity="low" />
      {unlocking ? <UnlockOverlay onComplete={finishUnlock} /> : null}

      <div className="relative grid min-h-screen lg:grid-cols-2">
        <section className="relative hidden min-h-screen lg:block">
          <SecureAccessVisual className="absolute inset-0" />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-r from-canvas/10 via-transparent to-canvas/70"
          />
          <div className="pointer-events-none relative z-10 flex h-full min-h-screen flex-col justify-between p-10 xl:p-12">
            <div className="flex items-center gap-3 motion-safe:animate-[cnas-rise_0.55s_ease-out_both]">
              <div className="relative flex h-12 w-12 items-center justify-center">
                <span className="absolute inset-0 rounded-full border border-accent/30 motion-safe:animate-[cnas-ring-expand_0.7s_ease-out_forwards]" />
                <BrandMark size={32} className="relative" />
              </div>
              <div>
                <p className="text-sm font-semibold tracking-[0.16em] text-ink">CNAS</p>
                <p className="mt-0.5 text-2xs tracking-wide text-ink-faint">
                  Criminal Network Analysis System
                </p>
              </div>
            </div>

            <div className="max-w-sm space-y-5 font-mono text-2xs tracking-wide text-ink-faint">
              <p className="text-accent/80">CNAS // SECURE ACCESS</p>
              <p>SYSTEM READY</p>
              <ul className="space-y-1.5">
                <li className="flex items-center gap-2">
                  <span className="h-1 w-1 rounded-full bg-signal-low" />
                  AUTHENTICATION SERVICE
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1 w-1 rounded-full bg-signal-low" />
                  GRAPH ENGINE
                </li>
                <li className="flex items-center gap-2">
                  <span className="h-1 w-1 rounded-full bg-signal-low" />
                  AUDIT SYSTEM
                </li>
              </ul>
              <p className="max-w-[16rem] font-sans text-[11px] leading-relaxed tracking-normal text-ink-faint/80">
                Interface indicators for the sign-in workspace — not a live
                health feed.
              </p>
            </div>
          </div>
        </section>

        <section className="relative flex min-h-screen items-center justify-center border-line/60 px-4 py-10 sm:px-8 lg:border-l">
          <div className="pointer-events-none absolute inset-0 lg:hidden">
            <SecureAccessVisual interactive={false} className="opacity-35" />
            <div className="absolute inset-0 bg-canvas/75" />
          </div>
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 hidden bg-canvas/45 lg:block"
          />

          <div className="relative w-full max-w-[420px] motion-safe:animate-[cnas-rise_0.6s_ease-out_both]">
            <TransitionLink
              to="/"
              className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-ink-muted transition-colors hover:text-ink"
            >
              <ArrowLeft size={13} strokeWidth={1.75} />
              Back to CNAS
            </TransitionLink>

            <div className="mb-8 flex items-center gap-3 lg:hidden">
              <div className="relative flex h-11 w-11 items-center justify-center">
                <span className="absolute inset-0 rounded-full border border-accent/30 motion-safe:animate-[cnas-ring-expand_0.7s_ease-out_forwards]" />
                <BrandMark size={28} className="relative" />
              </div>
              <div>
                <p className="text-sm font-semibold tracking-[0.16em] text-ink">CNAS</p>
                <p className="text-2xs text-ink-faint">Secure access</p>
              </div>
            </div>

            <div className="rounded-2xl border border-line-strong bg-surface/70 p-6 shadow-[0_24px_60px_-28px_rgba(0,0,0,0.75)] backdrop-blur-md sm:p-8">
              <p className="text-2xs font-semibold tracking-[0.18em] text-accent uppercase">
                Investigation workspace
              </p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
                Secure Access
              </h1>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                Continue to the CNAS investigation workspace.
              </p>

              <form
                className="mt-7 space-y-4"
                onSubmit={handleSubmit}
                aria-busy={isSubmitting || unlocking}
              >
                <LoginField
                  id="login-username"
                  label="Username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  autoFocus
                  error={hasAuthError}
                  value={username}
                  onChange={(event) => {
                    setUsername(event.target.value)
                    if (error) setError(null)
                  }}
                  disabled={isSubmitting || unlocking}
                />

                <LoginPasswordField
                  id="login-password"
                  label="Password"
                  name="password"
                  autoComplete="current-password"
                  error={hasAuthError}
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value)
                    if (error) setError(null)
                  }}
                  disabled={isSubmitting || unlocking}
                />

                {displayError ? (
                  <div
                    role="alert"
                    className="flex items-start gap-2 rounded-[10px] border border-signal-critical/40 bg-signal-critical/10 px-3 py-2.5"
                  >
                    <CircleAlert
                      size={14}
                      strokeWidth={1.75}
                      className="mt-0.5 shrink-0 text-signal-critical"
                    />
                    <p className="text-xs leading-relaxed text-signal-critical">{displayError}</p>
                  </div>
                ) : null}

                <CtaButton
                  type="submit"
                  className="mt-2 w-full tracking-[0.14em]"
                  disabled={
                    isSubmitting ||
                    unlocking ||
                    username.trim() === '' ||
                    password === ''
                  }
                >
                  {ctaCopy(isSubmitting, unlocking, entering)}
                </CtaButton>
              </form>

              <ul className="mt-8 grid grid-cols-2 gap-2 border-t border-line/80 pt-5">
                {TRUST_POINTS.map(({ icon: Icon, label }) => (
                  <li
                    key={label}
                    className="flex items-center gap-2 text-2xs text-ink-faint"
                  >
                    <Icon size={12} strokeWidth={1.75} className="text-accent/80" />
                    {label}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
