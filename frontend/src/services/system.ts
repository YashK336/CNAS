import { http } from './api'
import type { RequestOptions } from './api'
import type { ServiceInfo } from '@/types'

/** Root endpoint, used as the backend reachability probe. */
export function fetchServiceInfo(
  options?: RequestOptions,
): Promise<ServiceInfo> {
  return http.get<ServiceInfo>('/', options)
}
