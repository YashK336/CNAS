import { Download, FileText } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui'
import { downloadReport } from '@/services'
import type { ReportFormat, ReportSource } from '@/services/reports'
import { toErrorMessage } from '@/services'

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export interface ReportExportButtonsProps {
  source: ReportSource
  id: string
}

export function ReportExportButtons({ source, id }: ReportExportButtonsProps) {
  const [pendingFormat, setPendingFormat] = useState<ReportFormat | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function exportReport(format: ReportFormat) {
    setPendingFormat(format)
    setError(null)
    setSuccess(null)
    try {
      const { blob, filename } = await downloadReport(source, id, format)
      triggerDownload(blob, filename)
      setSuccess(`${format.toUpperCase()} download started.`)
    } catch (caught) {
      setError(toErrorMessage(caught))
    } finally {
      setPendingFormat(null)
    }
  }

  const busy = pendingFormat !== null

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap justify-end gap-1.5">
        <Button
          size="sm"
          variant="ghost"
          disabled={busy || !id}
          onClick={() => void exportReport('pdf')}
          icon={
            pendingFormat === 'pdf' ? (
              <Download size={13} strokeWidth={1.75} className="animate-pulse" />
            ) : (
              <FileText size={13} strokeWidth={1.75} />
            )
          }
        >
          {pendingFormat === 'pdf' ? 'Generating PDF…' : 'Export PDF'}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={busy || !id}
          onClick={() => void exportReport('json')}
          icon={
            pendingFormat === 'json' ? (
              <Download size={13} strokeWidth={1.75} className="animate-pulse" />
            ) : (
              <FileText size={13} strokeWidth={1.75} />
            )
          }
        >
          {pendingFormat === 'json' ? 'Generating JSON…' : 'Export JSON'}
        </Button>
      </div>
      {error ? (
        <p className="max-w-xs text-right text-2xs text-danger" role="alert">
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="max-w-xs text-right text-2xs text-ink-muted" role="status">
          {success}
        </p>
      ) : null}
    </div>
  )
}
