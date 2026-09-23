/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the CNAS FastAPI backend (Vercel production). */
  readonly VITE_API_URL?: string
  /** Local-dev alias; used when VITE_API_URL is unset. */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
