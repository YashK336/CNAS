import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import {
  clearAuthSession,
  getCurrentUser,
  isUnauthorized,
  login as loginRequest,
  readStoredAuthToken,
  setAuthToken,
  toErrorMessage,
} from '@/services'
import type { AuthUser, LoginRequest } from '@/types'

export interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isInitializing: boolean
  authError: string | null
  sessionExpiredMessage: string | null
  canReadInvestigations: boolean
  canWriteInvestigations: boolean
  canReadGovernance: boolean
  canAdjudicate: boolean
  isAdmin: boolean
  login: (payload: LoginRequest) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  clearSessionExpiredMessage: () => void
  handleUnauthorizedResponse: (requestUrl: string | null) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const SESSION_EXPIRED_MESSAGE =
  'Your session has expired. Sign in again to continue.'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState<
    string | null
  >(null)

  const clearSessionExpiredMessage = useCallback(() => {
    setSessionExpiredMessage(null)
  }, [])

  const handleUnauthorizedResponse = useCallback(
    (requestUrl: string | null) => {
      if (requestUrl?.includes('/auth/login')) {
        return
      }

      if (!readStoredAuthToken() && user === null) {
        return
      }

      clearAuthSession()
      setUser(null)
      setSessionExpiredMessage(SESSION_EXPIRED_MESSAGE)
    },
    [user],
  )

  const refreshUser = useCallback(async () => {
    const token = readStoredAuthToken()
    if (!token) {
      setUser(null)
      return
    }

    setAuthToken(token)
    try {
      const profile = await getCurrentUser()
      setUser(profile)
      setAuthError(null)
      setSessionExpiredMessage(null)
    } catch (error) {
      if (isUnauthorized(error)) {
        clearAuthSession()
        setUser(null)
        setSessionExpiredMessage(SESSION_EXPIRED_MESSAGE)
      } else {
        setAuthError(toErrorMessage(error))
      }
    }
  }, [])

  useEffect(() => {
    void refreshUser().finally(() => {
      setIsInitializing(false)
    })
  }, [refreshUser])

  const login = useCallback(async (payload: LoginRequest) => {
    setAuthError(null)
    setSessionExpiredMessage(null)
    const response = await loginRequest(payload)
    setUser(response.user)
  }, [])

  const logout = useCallback(() => {
    clearAuthSession()
    setUser(null)
    setAuthError(null)
    setSessionExpiredMessage(null)
  }, [])

  const value = useMemo<AuthContextValue>(() => {
    const role = user?.role
    return {
      user,
      isAuthenticated: user !== null,
      isInitializing,
      authError,
      sessionExpiredMessage,
      canReadInvestigations:
        role === 'ADMIN' || role === 'ANALYST' || role === 'VIEWER',
      canWriteInvestigations: role === 'ADMIN' || role === 'ANALYST',
      canReadGovernance:
        role === 'ADMIN' || role === 'ANALYST' || role === 'VIEWER',
      canAdjudicate: role === 'ADMIN' || role === 'ANALYST',
      isAdmin: role === 'ADMIN',
      login,
      logout,
      refreshUser,
      clearSessionExpiredMessage,
      handleUnauthorizedResponse,
    }
  }, [
    user,
    isInitializing,
    authError,
    sessionExpiredMessage,
    login,
    logout,
    refreshUser,
    clearSessionExpiredMessage,
    handleUnauthorizedResponse,
  ])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider')
  }
  return context
}
