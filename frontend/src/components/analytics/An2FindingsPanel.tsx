import { ChevronDown, ExternalLink, FileSearch, ScanSearch } from 'lucide-react'
import { useState } from 'react'

import {
  Badge,
  Button,
  EmptyState,
  Panel,
  PanelBody,
  PanelHeader,
  SectionError,
  Skeleton,
} from '@/components/ui'
import { fetchAn2Findings } from '@/services'
import { toErrorMessage } from '@/services/api'
import type { An2Finding, An2FindingsResponse } from '@/types'
import { parseAn2Records } from '@/lib/an2Input'
import { formatDate, formatDateTime, formatNumber } from '@/lib/format'

const INPUT_HINT = `[
  {
    "source": "unstructured_fir",
    "source_ref": "FIR-DEL-001",
    "jurisdiction": "DEL",
    "text": "Phone +91-90000-10001 observed...",
    "metadata": { "event_date": "2026-01-02" }
  }
]`

function confidenceTone(confidence: number) {
  if (confidence >= 0.8) return 'high' as const
  if (confidence >= 0.55) return 'medium' as const
  return 'neutral' as const
}

function FindingCard({ finding }: { finding: An2Finding }) {
  const [evidenceOpen, setEvidenceOpen] = useState(false)

  return (
    <article className="overflow-hidden rounded-md border border-line bg-surface-raised shadow-[0_10px_35px_rgb(0_0_0/0.12)]">
      <div className="border-b border-line px-4 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge tone="accent" mono>{finding.finding_type}</Badge>
              <Badge tone={confidenceTone(finding.confidence)} mono>
                {Math.round(finding.confidence * 100)}% confidence
              </Badge>
              <span className="font-mono text-2xs text-ink-faint">{finding.finding_id}</span>
            </div>
            <h3 className="truncate font-mono text-sm font-semibold text-ink">
              {finding.identifier.type}: {finding.identifier.value}
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-2 text-right">
            {[
              ['Cases', finding.cases.length],
              ['Jurisdictions', finding.jurisdictions.length],
            ].map(([label, value]) => (
              <div key={label} className="rounded-sm border border-line bg-surface px-2.5 py-2">
                <p className="text-2xs tracking-wider text-ink-faint uppercase">{label}</p>
                <p className="mt-1 font-mono text-base text-ink">{value}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="mt-4 text-sm leading-relaxed text-ink">{finding.claim}</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {finding.cases.map((caseRef) => (
            <a key={caseRef} href={`/cases/${encodeURIComponent(caseRef)}`} className="inline-flex items-center gap-1 rounded-sm border border-line-strong bg-surface px-2 py-1 font-mono text-2xs text-ink-muted transition-colors hover:border-accent/50 hover:text-accent">
              {caseRef}<ExternalLink size={10} strokeWidth={1.75} aria-hidden />
            </a>
          ))}
        </div>
      </div>

      <div className="grid gap-4 border-b border-line px-4 py-4 md:grid-cols-2">
        <div>
          <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">Temporal range</p>
          <p className="mt-1 font-mono text-xs text-ink-muted">{formatDate(finding.valid_from)} → {formatDate(finding.valid_to)}</p>
        </div>
        <div>
          <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">Jurisdictions</p>
          <p className="mt-1 text-xs text-ink-muted">{finding.jurisdictions.join(' · ')}</p>
        </div>
      </div>

      <div className="grid gap-4 px-4 py-4 md:grid-cols-2">
        <div>
          <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">Method</p>
          <p className="mt-1 font-mono text-xs text-ink">{finding.method.name}</p>
          <p className="mt-1 text-xs leading-relaxed text-ink-muted">Requires at least {finding.method.min_distinct_cases} distinct cases across {finding.method.min_jurisdictions} jurisdictions; deduplicates by {finding.method.deduplication_key}.</p>
        </div>
        <div>
          <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">Limits</p>
          <ul className="mt-1 space-y-1 text-xs leading-relaxed text-ink-muted">{finding.limits.map((limit) => <li key={limit}>• {limit}</li>)}</ul>
        </div>
      </div>

      <div className="border-t border-line bg-surface px-4 py-2">
        <button type="button" className="flex w-full items-center justify-between text-left text-xs text-ink-muted transition-colors hover:text-ink" onClick={() => setEvidenceOpen((open) => !open)} aria-expanded={evidenceOpen}>
          <span className="flex items-center gap-2"><FileSearch size={13} strokeWidth={1.75} />Evidence and provenance <span className="font-mono text-2xs text-ink-faint">{formatNumber(finding.evidence.length)} sources</span></span>
          <ChevronDown size={14} className={evidenceOpen ? 'rotate-180 transition-transform' : 'transition-transform'} />
        </button>
        {evidenceOpen ? <div className="mt-3 space-y-2 border-t border-line pt-3">{finding.evidence.map((evidence) => <div key={`${evidence.record_id}-${evidence.content_hash}`} className="rounded-sm border border-line px-3 py-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2"><a href={`/cases/${encodeURIComponent(evidence.case_ref)}`} className="font-mono text-xs text-accent hover:text-accent-hover">{evidence.source_ref}</a><span className="font-mono text-2xs text-ink-faint">{formatDateTime(evidence.ingested_at)}</span></div>
          <p className="mt-1 text-2xs text-ink-muted">{evidence.jurisdiction} · {evidence.record_id} · {evidence.content_hash.slice(0, 12)}…</p>
          {evidence.source_text ? <p className="mt-2 text-xs leading-relaxed text-ink-muted">“{evidence.source_text}”</p> : null}
        </div>)}</div> : null}
      </div>
    </article>
  )
}

export function An2FindingsPanel() {
  const [input, setInput] = useState('')
  const [response, setResponse] = useState<An2FindingsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const scan = async () => {
    setError(null)
    setResponse(null)
    setIsLoading(true)
    try {
      const records = parseAn2Records(input)
      if (records.length === 0) throw new Error('Add at least one FIR record to scan.')
      setResponse(await fetchAn2Findings(records))
    } catch (scanError) {
      setError(toErrorMessage(scanError))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Panel className="overflow-hidden">
      <PanelHeader eyebrow="AN-2 recurrence detector" title="Cross-record findings" description="Submit an unstructured FIR batch to surface identifiers recurring across cases and jurisdictions. Findings are computed for this session and are not persisted yet." icon={<ScanSearch size={15} strokeWidth={1.75} />} />
      <PanelBody className="space-y-4">
        <div className="grid gap-4 xl:grid-cols-[minmax(280px,0.72fr)_minmax(0,1.28fr)]">
          <div className="space-y-3"><div><p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">Investigator input</p><p className="mt-1 text-xs leading-relaxed text-ink-muted">Paste a JSON array or CSV with fir_id,raw_text or fir_id,jurisdiction,raw_text headers. JSON records still use source, reference, jurisdiction, and narrative text.</p></div><Button size="sm" onClick={scan} disabled={isLoading || !input.trim()} icon={<ScanSearch size={13} strokeWidth={1.75} />}>{isLoading ? 'Scanning batch' : 'Scan FIR batch'}</Button></div>
          <textarea value={input} onChange={(event) => setInput(event.target.value)} placeholder={INPUT_HINT} aria-label="Unstructured FIR batch" className="min-h-44 w-full resize-y rounded-sm border border-line-strong bg-canvas px-3 py-2.5 font-mono text-xs leading-relaxed text-ink placeholder:text-ink-faint focus:border-accent/60 focus:outline-none" spellCheck={false} />
        </div>
        {error ? <SectionError message={error} /> : null}
        {isLoading ? <div className="space-y-3" aria-label="Loading findings"><Skeleton className="h-40 w-full" /><Skeleton className="h-28 w-full" /></div> : null}
        {response && response.data.length === 0 ? <EmptyState icon={<FileSearch size={16} strokeWidth={1.75} />} title="No recurrence findings" description="No identifier met the AN-2 threshold in this batch: at least three distinct cases and two jurisdictions." /> : null}
        {response && response.data.length > 0 ? <div className="space-y-3"><div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-4"><p className="text-xs text-ink-muted"><span className="font-mono text-ink">{formatNumber(response.total)}</span> finding{response.total === 1 ? '' : 's'} returned for this batch.</p><Badge tone="neutral" mono>session result</Badge></div>{response.data.map((finding) => <FindingCard key={finding.finding_id} finding={finding} />)}</div> : null}
      </PanelBody>
    </Panel>
  )
}
