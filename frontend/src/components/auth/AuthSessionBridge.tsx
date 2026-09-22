import { useEffect } from 'react'

import { registerUnauthorizedHandler } from '@/services'
import { useAuth } from '@/hooks/useAuth'

/**
 * Connects global 401 handling to auth state. Mounted inside the router so
 * expired sessions redirect through the existing RequireAuth boundary.
 */
export function AuthSessionBridge() {
  const { handleUnauthorizedResponse } = useAuth()

  useEffect(() => {
    registerUnauthorizedHandler((requestUrl) => {
      handleUnauthorizedResponse(requestUrl)
    })
    return () => registerUnauthorizedHandler(null)
  }, [handleUnauthorizedResponse])

  return null
}
