import { http, setAuthToken } from './api'
import type { RequestOptions } from './api'
import type { AuthUser, LoginRequest, LoginResponse } from '@/types'

export function login(
  payload: LoginRequest,
  options?: RequestOptions,
): Promise<LoginResponse> {
  return http.post<LoginResponse>('/auth/login', payload, options).then((response) => {
    setAuthToken(response.access_token)
    return response
  })
}

export function getCurrentUser(options?: RequestOptions): Promise<AuthUser> {
  return http.get<AuthUser>('/auth/me', options)
}

export function clearAuthSession(): void {
  setAuthToken(null)
}
