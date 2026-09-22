import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { Skeleton } from '@/components/ui'
import { useAuth } from '@/hooks/useAuth'
import { LandingPage } from '@/pages/LandingPage'

/**
 * Application-wide authentication boundary for CNAS modules.
 *
 * The root path is the one exception to the "redirect to /login" rule: an
 * unauthenticated visit to `/` renders the public marketing landing page
 * instead of bouncing straight to the sign-in form, so the product has a
 * front door before authentication. Every other protected path keeps the
 * original redirect-to-login behaviour unchanged.
 */
export function RequireAuth() {
  const { isAuthenticated, isInitializing, sessionExpiredMessage } = useAuth()
  const location = useLocation()

  if (isInitializing) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (!isAuthenticated) {
    if (location.pathname === '/') {
      return <LandingPage />
    }

    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: `${location.pathname}${location.search}`,
          sessionExpired: sessionExpiredMessage !== null,
        }}
      />
    )
  }

  return <Outlet />
}
