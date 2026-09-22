/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the CNAS FastAPI backend. */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
