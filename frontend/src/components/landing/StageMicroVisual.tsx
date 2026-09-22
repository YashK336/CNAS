export type StageVisualKind = 'gather' | 'understand' | 'connect' | 'analyze' | 'verify'

/**
 * Tiny, continuously-looping SVG illustration for a "how it works" stage
 * card. Kept deliberately small and low-amplitude — a bit of ambient life
 * per card rather than a demonstration in itself.
 */
export function StageMicroVisual({ kind }: { kind: StageVisualKind }) {
  switch (kind) {
    case 'gather':
      return (
        <svg viewBox="0 0 40 40" className="h-9 w-9" aria-hidden>
          {[0, 1, 2].map((i) => (
            <rect
              key={i}
              x={11 - i * 2}
              y={22 - i * 4}
              width={18}
              height={13}
              rx={2}
              className="fill-surface stroke-line-strong"
              strokeWidth={1.1}
              style={{
                transformOrigin: 'center',
                animation: `cnas-bob 3.2s ease-in-out ${i * 0.25}s infinite`,
              }}
            />
          ))}
        </svg>
      )

    case 'understand':
      return (
        <svg viewBox="0 0 40 40" className="h-9 w-9" aria-hidden>
          <rect x={8} y={12} width={24} height={16} rx={2} className="fill-surface stroke-line-strong" strokeWidth={1.1} />
          <clipPath id="understand-clip">
            <rect x={8} y={12} width={24} height={16} rx={2} />
          </clipPath>
          <g clipPath="url(#understand-clip)">
            <rect
              x={-8}
              y={12}
              width={10}
              height={16}
              className="fill-accent/20"
              style={{ animation: 'cnas-flow-x 3s linear infinite' }}
            />
          </g>
          <line x1={13} y1={18} x2={23} y2={18} className="stroke-ink-faint/70" strokeWidth={1} />
          <line x1={13} y1={22} x2={20} y2={22} className="stroke-ink-faint/50" strokeWidth={1} />
        </svg>
      )

    case 'connect':
      return (
        <svg viewBox="0 0 40 40" className="h-9 w-9" aria-hidden>
          <circle cx={11} cy={26} r={4} className="fill-surface-raised stroke-accent" strokeWidth={1.25} />
          <circle cx={29} cy={14} r={4} className="fill-surface-raised stroke-accent" strokeWidth={1.25} />
          <line
            x1={14.5}
            y1={23.5}
            x2={25.5}
            y2={16.5}
            className="stroke-accent/70"
            strokeWidth={1.4}
            strokeDasharray="3 3"
            style={{ animation: 'cnas-flow 2.2s linear infinite' }}
          />
        </svg>
      )

    case 'analyze':
      return (
        <svg viewBox="0 0 40 40" className="h-9 w-9" aria-hidden>
          {[0, 1, 2, 3].map((i) => (
            <rect
              key={i}
              x={9 + i * 6}
              y={12}
              width={3.5}
              height={18}
              rx={1}
              className={i === 2 ? 'fill-accent/70' : 'fill-line-strong'}
              style={{
                transformOrigin: 'bottom',
                transformBox: 'fill-box',
                animation: `cnas-bar-pulse ${2.4 + i * 0.2}s ease-in-out ${i * 0.15}s infinite`,
              }}
            />
          ))}
        </svg>
      )

    case 'verify':
      return (
        <svg viewBox="0 0 40 40" className="h-9 w-9" aria-hidden>
          <circle cx={20} cy={20} r={12} className="fill-surface-raised stroke-line-strong" strokeWidth={1.25} />
          <path
            d="M15 20.5 L18.5 24 L26 15.5"
            fill="none"
            className="stroke-accent"
            strokeWidth={1.75}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="16"
            style={{ animation: 'cnas-flow 3.4s ease-in-out infinite' }}
          />
        </svg>
      )

    default:
      return null
  }
}
