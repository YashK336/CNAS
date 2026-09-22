export interface BrandMarkProps {
  size?: number
  className?: string
}

/**
 * CNAS glyph: a three-node link diagram. Inline SVG so the mark inherits the
 * accent colour and needs no asset request.
 */
export function BrandMark({ size = 26, className }: BrandMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      role="img"
      aria-label="CNAS"
      className={className}
    >
      <rect
        x="0.75"
        y="0.75"
        width="22.5"
        height="22.5"
        rx="4.25"
        className="fill-surface-raised stroke-line-strong"
        strokeWidth="1.5"
      />
      <g className="stroke-accent" strokeWidth="1.25" strokeLinecap="round">
        <path d="M12 7.75 6.75 16.25" opacity="0.55" />
        <path d="M12 7.75 17.25 16.25" opacity="0.55" />
        <path d="M6.75 16.25h10.5" opacity="0.3" />
      </g>
      <g className="fill-accent">
        <circle cx="12" cy="7.75" r="2.15" />
        <circle cx="6.75" cy="16.25" r="1.5" opacity="0.75" />
        <circle cx="17.25" cy="16.25" r="1.5" opacity="0.75" />
      </g>
    </svg>
  )
}
