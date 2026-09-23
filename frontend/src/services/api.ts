import axios from 'axios'
import type { AxiosInstance } from 'axios'

const FALLBACK_BASE_URL = 'http://127.0.0.1:8000'

/** Trailing slashes are stripped so path joins stay predictable. */
export const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  FALLBACK_BASE_URL
).replace(/\/+$/, '')

export const REQUEST_TIMEOUT_MS = 30_000

const AUTH_TOKEN_STORAGE_KEY = 'cnas.auth.token'

type UnauthorizedHandler = (requestUrl: string | null) => void

let unauthorizedHandler: UnauthorizedHandler | null = null

/** Register a global handler for expired/invalid JWT responses. */
export function registerUnauthorizedHandler(
  handler: UnauthorizedHandler | null,
): void {
  unauthorizedHandler = handler
}

/** Attach bearer token for protected CNAS endpoints. */
export function setAuthToken(token: string | null): void {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`
    try {
      sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token)
    } catch {
      // Private browsing may block storage; in-memory header still applies.
    }
    return
  }

  delete api.defaults.headers.common.Authorization
  try {
    sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
  } catch {
    // Ignore storage failures on logout.
  }
}

export function readStoredAuthToken(): string | null {
  try {
    return sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

/** Options every service accepts so callers can cancel in-flight requests. */
export interface RequestOptions {
  signal?: AbortSignal
  /** Per-request override; defaults to `REQUEST_TIMEOUT_MS`. */
  timeout?: number
}

/** Normalised transport/HTTP failure surfaced to the UI. */
export class ApiError extends Error {
  readonly status: number | null
  readonly url: string | null
  readonly aborted: boolean

  constructor(
    message: string,
    details: { status?: number | null; url?: string | null; aborted?: boolean },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = details.status ?? null
    this.url = details.url ?? null
    this.aborted = details.aborted ?? false
  }
}

interface FastApiErrorBody {
  detail?: string | { msg?: string }[]
}

function readDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null

  const detail = (body as FastApiErrorBody).detail

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((msg): msg is string => Boolean(msg))
    if (messages.length > 0) return messages.join('; ')
  }

  return null
}

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? null
    const url = error.config?.url ?? null
    const aborted = error.code === 'ERR_CANCELED'

    if (aborted) {
      return new ApiError('Request cancelled', { status, url, aborted: true })
    }

    const detail = readDetail(error.response?.data)
    if (detail) return new ApiError(detail, { status, url })

    if (status) {
      return new ApiError(`Request failed with status ${status}`, {
        status,
        url,
      })
    }

    return new ApiError(
      `Cannot reach the CNAS backend at ${API_BASE_URL}`,
      { status, url },
    )
  }

  const message =
    error instanceof Error ? error.message : 'Unexpected request failure'

  return new ApiError(message, {})
}

async function blobErrorToApiError(error: unknown): Promise<ApiError> {
  if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
    const status = error.response.status ?? null
    const url = error.config?.url ?? null
    try {
      const text = await error.response.data.text()
      const parsed = JSON.parse(text) as FastApiErrorBody
      const detail = readDetail(parsed)
      if (detail) return new ApiError(detail, { status, url })
    } catch {
      // Fall through to the generic transport error.
    }
  }
  return toApiError(error)
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { Accept: 'application/json' },
})

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const apiError = toApiError(error)
    if (apiError.status === 401 && unauthorizedHandler) {
      unauthorizedHandler(apiError.url)
    }
    return Promise.reject(apiError)
  },
)

const storedToken = readStoredAuthToken()
if (storedToken) {
  api.defaults.headers.common.Authorization = `Bearer ${storedToken}`
}

/**
 * Thin typed wrapper so service modules never touch response envelopes.
 */
export const http = {
  get<T>(url: string, options?: RequestOptions): Promise<T> {
    return api.get<T>(url, options).then((response) => response.data)
  },

  post<T>(url: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return api
      .post<T>(url, body, options)
      .then((response) => response.data)
  },

  put<T>(url: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return api.put<T>(url, body, options).then((response) => response.data)
  },

  async getBlob(url: string, options?: RequestOptions): Promise<Blob> {
    try {
      const response = await api.get<Blob>(url, {
        ...options,
        responseType: 'blob',
      })
      return response.data
    } catch (error) {
      throw await blobErrorToApiError(error)
    }
  },
}

/** Extracts a display-ready message from any thrown request failure. */
export function toErrorMessage(error: unknown): string {
  return toApiError(error).message
}

/** True when a rejection came from an aborted/cancelled request. */
export function isAbortError(error: unknown): boolean {
  return error instanceof ApiError && error.aborted
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

export function isForbidden(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403
}
