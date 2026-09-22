import { useEffect, useRef, useState } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { useMediaQuery } from '@/hooks/useMediaQuery'

type ItemShape = 'circle' | 'square' | 'diamond'

interface Item {
  id: string
  x: number
  y: number
  shape: ItemShape
  docLabel: string
  entityLabel: string
  entityKind: string
  emphasis?: boolean
}

interface Edge {
  from: string
  to: string
}

const ITEMS: Item[] = [
  { id: 'case', x: 230, y: 44, shape: 'diamond', docLabel: 'FIR-2024-0182', entityLabel: 'FIR-2024-0182', entityKind: 'Case', emphasis: true },
  { id: 'person', x: 148, y: 142, shape: 'circle', docLabel: 'Witness statement', entityLabel: 'P104', entityKind: 'Person' },
  { id: 'phone', x: 56, y: 232, shape: 'square', docLabel: 'Call log', entityLabel: '+91 •••• 0142', entityKind: 'Phone' },
  { id: 'vehicle', x: 244, y: 236, shape: 'square', docLabel: 'Vehicle report', entityLabel: 'DL •• AB ••41', entityKind: 'Vehicle' },
  { id: 'location', x: 350, y: 150, shape: 'diamond', docLabel: 'Field note', entityLabel: 'Sector 21', entityKind: 'Location' },
]

const EDGES: Edge[] = [
  { from: 'case', to: 'person' },
  { from: 'person', to: 'phone' },
  { from: 'person', to: 'vehicle' },
  { from: 'case', to: 'location' },
]

const ITEM_LOOKUP = new Map(ITEMS.map((item) => [item.id, item]))

const STAGES = [
  { label: 'Fragmented documents', hint: 'FIRs and case notes arrive as free text.' },
  { label: 'Entities extracted', hint: 'People, phones, vehicles, and places are identified.' },
  { label: 'Connections mapped', hint: 'Extracted entities are linked into one graph.' },
  { label: 'Pattern surfaced', hint: 'A connection worth an analyst\u2019s attention stands out.' },
] as const

const STAGE_DURATION_MS = 2600

function DocGlyph({ item, visible }: { item: Item; visible: boolean }) {
  return (
    <g
      transform={`translate(${item.x}, ${item.y})`}
      style={{ opacity: visible ? 1 : 0, transition: 'opacity 500ms ease' }}
    >
      <path
        d="M -13 -16 L 6 -16 L 13 -9 L 13 16 L -13 16 Z M 6 -16 L 6 -9 L 13 -9"
        className="fill-surface-raised stroke-line-strong"
        strokeWidth={1.25}
        strokeLinejoin="round"
      />
      <line x1={-7} y1={-2} x2={7} y2={-2} className="stroke-ink-faint/70" strokeWidth={1} />
      <line x1={-7} y1={4} x2={3} y2={4} className="stroke-ink-faint/50" strokeWidth={1} />
      <text
        y={32}
        textAnchor="middle"
        className="fill-ink-faint"
        style={{ fontSize: 8.5, letterSpacing: '0.01em' }}
      >
        {item.docLabel}
      </text>
    </g>
  )
}

function EntityGlyph({
  item,
  visible,
  highlighted,
}: {
  item: Item
  visible: boolean
  highlighted: boolean
}) {
  const size = (item.shape === 'circle' ? 14 : 11) * (highlighted ? 1.15 : 1)
  const active = item.emphasis || highlighted
  const fill = active ? 'fill-accent/22' : 'fill-surface-raised'
  const stroke = active ? 'stroke-accent' : 'stroke-line-strong'
  const shared = {
    className: `${fill} ${stroke}`,
    strokeWidth: highlighted ? 2 : 1.4,
  }

  return (
    <g
      transform={`translate(${item.x}, ${item.y})`}
      style={{ opacity: visible ? 1 : 0, transition: 'opacity 500ms ease, transform 400ms ease' }}
    >
      {item.shape === 'circle' && <circle r={size} {...shared} />}
      {item.shape === 'diamond' && (
        <rect x={-size} y={-size} width={size * 2} height={size * 2} transform="rotate(45)" {...shared} />
      )}
      {item.shape === 'square' && (
        <rect x={-size} y={-size} width={size * 2} height={size * 2} rx={3} {...shared} />
      )}
      <text
        y={item.shape === 'circle' ? 28 : 24}
        textAnchor="middle"
        className="fill-ink"
        style={{ fontSize: 10, fontWeight: 600 }}
      >
        {item.entityLabel}
      </text>
      <text
        y={item.shape === 'circle' ? 40 : 36}
        textAnchor="middle"
        className="fill-ink-faint"
        style={{ fontSize: 8, letterSpacing: '0.06em', textTransform: 'uppercase' }}
      >
        {item.entityKind}
      </text>
    </g>
  )
}

function EdgeLine({ edge, visible, highlighted }: { edge: Edge; visible: boolean; highlighted: boolean }) {
  const from = ITEM_LOOKUP.get(edge.from)
  const to = ITEM_LOOKUP.get(edge.to)
  if (!from || !to) return null

  return (
    <line
      x1={from.x}
      y1={from.y}
      x2={to.x}
      y2={to.y}
      className={highlighted ? 'stroke-accent/80' : 'stroke-ink-faint/40'}
      strokeWidth={highlighted ? 1.75 : 1.1}
      style={{
        opacity: visible ? 1 : 0,
        transition: 'opacity 550ms ease, stroke 400ms ease',
      }}
    />
  )
}

/**
 * The hero's centrepiece: a self-looping, four-stage illustration of the
 * product's core idea (loose documents \u2192 identified entities \u2192 a
 * connected graph \u2192 a surfaced pattern). Reacts subtly to pointer
 * position and to hero scroll progress. Entirely synthetic — labelled as
 * illustrative in the surrounding copy, not wired to any data source.
 */
export function TransformationVisual() {
  const prefersReducedMotion = usePrefersReducedMotion()
  const isSmallViewport = useMediaQuery('(max-width: 640px)')
  const [stage, setStage] = useState(prefersReducedMotion ? 3 : 0)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (prefersReducedMotion) return
    const interval = window.setInterval(() => {
      setStage((current) => (current + 1) % STAGES.length)
    }, STAGE_DURATION_MS)
    return () => window.clearInterval(interval)
  }, [prefersReducedMotion])

  // Subtle pointer parallax + hero scroll progress — both feed the same
  // translate transform on the scene, so the effect stays a single,
  // predictable motion rather than two competing ones.
  useEffect(() => {
    if (prefersReducedMotion || isSmallViewport) return
    const wrapper = wrapperRef.current
    const scene = sceneRef.current
    if (!wrapper || !scene) return

    let pointerX = 0
    let pointerY = 0
    let scrollOffset = 0
    let pendingFrame = 0

    const apply = () => {
      pendingFrame = 0
      scene.style.transform = `translate3d(${pointerX.toFixed(2)}px, ${(pointerY + scrollOffset).toFixed(2)}px, 0)`
    }

    const schedule = () => {
      if (pendingFrame) return
      pendingFrame = window.requestAnimationFrame(apply)
    }

    const handlePointerMove = (event: PointerEvent) => {
      const rect = wrapper.getBoundingClientRect()
      const relX = (event.clientX - rect.left) / rect.width - 0.5
      const relY = (event.clientY - rect.top) / rect.height - 0.5
      pointerX = relX * -10
      pointerY = relY * -8
      schedule()
    }

    const handleScroll = () => {
      const rect = wrapper.getBoundingClientRect()
      const progress = Math.min(1, Math.max(0, 1 - rect.top / window.innerHeight))
      scrollOffset = progress * -14
      schedule()
    }

    window.addEventListener('pointermove', handlePointerMove, { passive: true })
    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll()

    return () => {
      if (pendingFrame) window.cancelAnimationFrame(pendingFrame)
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('scroll', handleScroll)
    }
  }, [prefersReducedMotion, isSmallViewport])

  const showDocs = stage === 0
  const showEntities = stage >= 1
  const showEdges = stage >= 2
  const showInsight = stage === 3

  return (
    <div ref={wrapperRef} className="relative">
      <div className="relative rounded-2xl border border-line-strong bg-surface-raised/80 p-4 shadow-[0_24px_60px_-32px_rgba(0,0,0,0.7)] backdrop-blur-sm sm:p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-2xs font-semibold tracking-widest text-ink-faint uppercase">
            From fragments to intelligence
          </p>
          <span className="rounded-sm border border-line-strong bg-surface px-1.5 py-0.5 text-2xs text-ink-faint">
            Illustrative
          </span>
        </div>

        <div ref={sceneRef} className="mt-3 transition-transform duration-300 ease-out will-change-transform">
          <svg viewBox="0 0 460 300" className="h-auto w-full" role="img" aria-label="Illustrative animation showing case documents resolving into people, phone, vehicle, and location entities, then connecting into a graph that surfaces one highlighted pattern.">
            {EDGES.map((edge) => (
              <EdgeLine key={`${edge.from}-${edge.to}`} edge={edge} visible={showEdges} highlighted={showInsight && edge.from === 'case' && edge.to === 'person'} />
            ))}
            {ITEMS.map((item) => (
              <DocGlyph key={`doc-${item.id}`} item={item} visible={showDocs} />
            ))}
            {ITEMS.map((item) => (
              <EntityGlyph
                key={`entity-${item.id}`}
                item={item}
                visible={showEntities}
                highlighted={showInsight && item.id === 'person'}
              />
            ))}
            {showInsight ? (
              <g transform="translate(148, 100)" style={{ opacity: 1, transition: 'opacity 400ms ease' }}>
                <rect x={-46} y={-14} width={92} height={20} rx={4} className="fill-canvas stroke-accent/60" strokeWidth={1} />
                <text textAnchor="middle" y={0} className="fill-accent font-mono" style={{ fontSize: 8.5, letterSpacing: '0.02em' }}>
                  pattern · conf 0.86
                </text>
              </g>
            ) : null}
          </svg>
        </div>

        <div className="mt-1 flex items-center justify-between gap-3 border-t border-line/70 pt-3">
          <div>
            <p className="text-xs font-semibold text-ink">{STAGES[stage]?.label}</p>
            <p className="mt-0.5 text-2xs leading-relaxed text-ink-faint">{STAGES[stage]?.hint}</p>
          </div>
          <div className="flex shrink-0 gap-1.5" aria-hidden>
            {STAGES.map((s, index) => (
              <span
                key={s.label}
                className={`h-1 w-4 rounded-full transition-colors duration-300 ${index === stage ? 'bg-accent' : 'bg-line-strong'}`}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
