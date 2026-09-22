/**
 * The backend wraps collection endpoints as `{ total, data }`.
 */
export interface ListResponse<T> {
  total: number
  data: T[]
}

/** Response of `GET /`. */
export interface ServiceInfo {
  message: string
}
