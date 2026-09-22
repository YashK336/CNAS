import { http } from './api'
import type { RequestOptions } from './api'

export type ReportFormat = 'json' | 'pdf'
export type ReportSource = 'investigation' | 'case'

function reportUrl(source: ReportSource, id: string, format: ReportFormat): string {
  const encoded = encodeURIComponent(id)
  const path =
    source === 'investigation'
      ? `/investigations/${encoded}/report`
      : `/cases/${encoded}/report`
  return `${path}?format=${format}`
}

function reportFilename(source: ReportSource, id: string, format: ReportFormat): string {
  const prefix = source === 'investigation' ? 'cnas-investigation' : 'cnas-case'
  return `${prefix}-${id}.${format}`
}

export async function downloadReport(
  source: ReportSource,
  id: string,
  format: ReportFormat,
  options?: RequestOptions,
): Promise<{ filename: string; blob: Blob }> {
  const blob = await http.getBlob(reportUrl(source, id, format), {
    ...options,
    timeout: options?.timeout ?? 60_000,
  })
  return { filename: reportFilename(source, id, format), blob }
}
