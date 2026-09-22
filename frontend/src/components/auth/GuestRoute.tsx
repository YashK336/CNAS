import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useAuth } from '@/hooks/useAuth'

/**
 * Guest-only wrapper for the sign-in screen.
 *
 * Authenticated visits still render children so `LoginPage` can play its
 * short post-auth unlock before committing navigation. Already-authenticated
 * arrivals are bounced from inside `LoginPage` without that overlay.
 */
export function GuestRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()
  const redirectTo =
    (location.state as { from?: string } | null)?.from ?? '/'

  if (isInitializing) {
    return <div className="min-h-screen bg-canvas" aria-busy="true" />
  }

  if (isAuthenticated && location.pathname !== '/login') {
    return <Navigate to={redirectTo} replace />
  }

  return children
}
