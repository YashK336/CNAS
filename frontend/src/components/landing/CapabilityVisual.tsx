import type { CSSProperties } from 'react'

export type CapabilityVisualKind =
  | 'network'
  | 'resolution'
  | 'fir'
  | 'risk'
  | 'anomaly'
  | 'evidence'
  | 'jurisdiction'
  | 'adjudication'
  | 'collaboration'

/**
 * Small, continuously-looping illustration shown inside a capability
 * card — a few seconds of restrained motion per card rather than a static
 * icon, without becoming a second data visualization to read.
 */
export function CapabilityVisual({ kind }: { kind: CapabilityVisualKind }) {
  switch (kind) {
    case 'network':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          <line x1={14} y1={28} x2={32} y2={12} className="stroke-ink-faint/50" strokeWidth={1} />
          <line x1={32} y1={12} x2={50} y2={26} className="stroke-ink-faint/50" strokeWidth={1} />
          <line x1={14} y1={28} x2={50} y2={26} className="stroke-ink-faint/30" strokeWidth={1} />
          <circle cx={14} cy={28} r={3.2} className="fill-surface-raised stroke-accent" strokeWidth={1.1} style={{ animation: 'cnas-pulse-soft 3.4s ease-in-out infinite' }} />
          <circle cx={32} cy={12} r={3.6} className="fill-accent/25 stroke-accent" strokeWidth={1.1} />
          <circle cx={50} cy={26} r={3.2} className="fill-surface-raised stroke-accent" strokeWidth={1.1} style={{ animation: 'cnas-pulse-soft 3.4s ease-in-out 0.6s infinite' }} />
        </svg>
      )

    case 'resolution':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          <circle
            cx={22}
            cy={20}
            r={7}
            className="fill-surface stroke-line-strong"
            strokeWidth={1.1}
            style={{ transformOrigin: '22px 20px', animation: 'cnas-merge 2.8s ease-in-out infinite', ['--dx' as string]: '5px' } as CSSProperties}
          />
          <circle
            cx={42}
            cy={20}
            r={7}
            className="fill-surface stroke-accent"
            strokeWidth={1.1}
            style={{ transformOrigin: '42px 20px', animation: 'cnas-merge 2.8s ease-in-out infinite', ['--dx' as string]: '-5px' } as CSSProperties}
          />
        </svg>
      )

    case 'fir':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          <rect x={20} y={7} width={24} height={26} rx={2} className="fill-surface stroke-line-strong" strokeWidth={1.1} />
          <line x1={25} y1={15} x2={39} y2={15} className="stroke-ink-faint/60" strokeWidth={1} />
          <line x1={25} y1={20} x2={39} y2={20} className="stroke-ink-faint/45" strokeWidth={1} />
          <line x1={25} y1={25} x2={34} y2={25} className="stroke-ink-faint/45" strokeWidth={1} />
          <clipPath id="fir-scan-clip">
            <rect x={20} y={7} width={24} height={26} rx={2} />
          </clipPath>
          <g clipPath="url(#fir-scan-clip)">
            <rect x={4} y={7} width={8} height={26} className="fill-accent/20" style={{ animation: 'cnas-flow-x 2.8s linear infinite' }} />
          </g>
        </svg>
      )

    case 'risk':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          <path d="M14 30 A18 18 0 0 1 50 30" fill="none" className="stroke-line-strong" strokeWidth={2.5} strokeLinecap="round" />
          <path
            d="M14 30 A18 18 0 0 1 50 30"
            fill="none"
            className="stroke-signal-medium"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeDasharray="62"
            style={{ animation: 'cnas-flow 3.2s ease-in-out infinite' }}
          />
          <circle cx={41} cy={16.5} r={2} className="fill-signal-medium" />
        </svg>
      )

    case 'anomaly':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          {[12, 22, 32, 42, 52].map((x, i) => (
            <circle
              key={x}
              cx={x}
              cy={22}
              r={i === 2 ? 3.4 : 2.4}
              className={i === 2 ? 'fill-signal-critical' : 'fill-line-strong'}
              style={i === 2 ? { animation: 'cnas-pulse-soft 2.4s ease-in-out infinite' } : undefined}
            />
          ))}
          <line x1={4} y1={12} x2={4} y2={32} className="stroke-signal-critical/50" strokeWidth={1.4} style={{ animation: 'cnas-flow-x 3.4s linear infinite' }} />
        </svg>
      )

    case 'evidence':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          <rect x={16} y={11} width={20} height={20} rx={2} className="fill-surface stroke-line-strong" strokeWidth={1.1} />
          <rect x={22} y={17} width={20} height={20} rx={2} className="fill-surface-raised stroke-accent" strokeWidth={1.1} style={{ animation: 'cnas-bob 3.6s ease-in-out infinite' }} />
          <path d="M27 27 L30.5 30.5 L37 24" fill="none" className="stroke-accent" strokeWidth={1.4} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )

    case 'jurisdiction':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          <rect x={9} y={13} width={14} height={14} rx={3} className="fill-surface stroke-line-strong" strokeWidth={1.1} />
          <rect x={41} y={13} width={14} height={14} rx={3} className="fill-surface stroke-line-strong" strokeWidth={1.1} />
          <line x1={23} y1={20} x2={41} y2={20} className="stroke-accent/70" strokeWidth={1.3} strokeDasharray="3 3" style={{ animation: 'cnas-flow 2.6s linear infinite' }} />
        </svg>
      )

    case 'adjudication':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          <rect x={16} y={8} width={32} height={24} rx={3} className="fill-surface stroke-line-strong" strokeWidth={1.1} />
          {[13, 19, 25].map((y) => (
            <line key={y} x1={22} y1={y} x2={36} y2={y} className="stroke-ink-faint/45" strokeWidth={1} />
          ))}
          <g transform="translate(40, 26)">
            <circle r={6} className="fill-canvas stroke-accent" strokeWidth={1.1} />
            <path
              d="M-2.6 0 L-0.6 2 L2.8 -2.4"
              fill="none"
              className="stroke-accent"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="8"
              style={{ animation: 'cnas-flow 3s ease-in-out infinite' }}
            />
          </g>
        </svg>
      )

    case 'collaboration':
      return (
        <svg viewBox="0 0 64 40" className="h-9 w-16" aria-hidden>
          <circle cx={22} cy={18} r={6} className="fill-surface stroke-line-strong" strokeWidth={1.1} />
          <circle cx={40} cy={24} r={6} className="fill-surface stroke-accent" strokeWidth={1.1} />
          <path d="M31 12 L36 16" className="stroke-ink-faint/60" strokeWidth={1.2} strokeLinecap="round" style={{ animation: 'cnas-bob 3s ease-in-out infinite' }} />
        </svg>
      )

    default:
      return null
  }
}
