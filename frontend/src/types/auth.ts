/** Authentication types from `/auth` endpoints. */

export type UserRole = 'ADMIN' | 'ANALYST' | 'VIEWER'

export interface AuthUser {
  id: string
  username: string
  role: UserRole
  jurisdictions: string[]
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  user: AuthUser
}
