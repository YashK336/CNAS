import { Bookmark } from 'lucide-react'
import { Link } from 'react-router-dom'

import { formatText } from '@/lib/format'
import type { SavedInvestigation } from '@/types'

export interface InvestigationWorkspaceBannerProps {
  investigation: SavedInvestigation | null
  restoreError?: string | null
}

export function InvestigationWorkspaceBanner({
  investigation,
  restoreError,
}: InvestigationWorkspaceBannerProps) {
  if (!investigation && !restoreError) return null

  return (
    <div className="rounded-sm border border-line bg-surface-raised px-3 py-2">
      {investigation ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="text-2xs tracking-widest text-ink-faint uppercase">
              Active investigation
            </p>
            <p className="truncate text-sm font-medium text-ink">
              {formatText(investigation.name)}
            </p>
            <p className="mt-0.5 text-2xs text-ink-muted">
              {investigation.jurisdiction
                ? `Jurisdiction ${investigation.jurisdiction}`
                : 'Legacy / unscoped record'}
              {investigation.graph_seeds.length > 0
                ? ` · Seeds ${investigation.graph_seeds.join(', ')}`
                : ''}
            </p>
          </div>

          <Link
            to="/investigations"
            className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
          >
            <Bookmark size={13} strokeWidth={1.75} />
            Saved investigations
          </Link>
        </div>
      ) : null}

      {restoreError ? (
        <p className="mt-2 text-xs text-signal-high">{restoreError}</p>
      ) : null}
    </div>
  )
}
