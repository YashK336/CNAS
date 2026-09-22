import { useEffect, useRef, useState } from 'react'

import { useMediaQuery } from '@/hooks/useMediaQuery'
import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { cn } from '@/lib/cn'

interface AmbientNode {
  x: number
  y: number
  homeX: number
  homeY: number
  vx: number
  vy: number
  r: number
}

interface Packet {
  from: number
  t: number
  speed: number
}

interface NamedNode {
  id: string
  label: string
  detail: string
  angle: number
  radius: number
}

const NODE_COLOR = '75, 141, 248'
const EDGE_COLOR = '106, 114, 125'
const HOVER_RADIUS = 110
const ATTRACT_STRENGTH = 0.0014

const NAMED: NamedNode[] = [
  { id: 'graph', label: 'Case graph', detail: 'Resolved entities and relationships', angle: -0.55, radius: 0.34 },
  { id: 'evidence', label: 'Evidence', detail: 'Source, method, confidence', angle: 2.15, radius: 0.3 },
  { id: 'workspace', label: 'Workspace', detail: 'Investigations and reviews', angle: 3.7, radius: 0.32 },
]

function createNodes(width: number, height: number, dense: boolean): AmbientNode[] {
  const cx = width * 0.52
  const cy = height * 0.5
  const count = dense ? 28 : 14

  return Array.from({ length: count }, (_, index) => {
    const angle = (index / count) * Math.PI * 2 + Math.random() * 0.4
    const dist = Math.min(width, height) * (0.18 + Math.random() * 0.32)
    const x = cx + Math.cos(angle) * dist
    const y = cy + Math.sin(angle) * dist
    return {
      x,
      y,
      homeX: x,
      homeY: y,
      vx: (Math.random() - 0.5) * 0.08,
      vy: (Math.random() - 0.5) * 0.08,
      r: Math.random() * 1.1 + 0.7,
    }
  })
}

export interface SecureAccessVisualProps {
  className?: string
  interactive?: boolean
}

/**
 * Illustrative secure-access visualization: a quiet node field that slowly
 * converges on a central hub, with data moving along a few edges. Decorative
 * only — labels describe the product, not live infrastructure status.
 */
export function SecureAccessVisual({
  className,
  interactive = true,
}: SecureAccessVisualProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const prefersReducedMotion = usePrefersReducedMotion()
  const hasFinePointer = useMediaQuery('(pointer: fine)')
  const [hovered, setHovered] = useState<NamedNode | null>(null)
  const hoveredRef = useRef<NamedNode | null>(null)

  useEffect(() => {
    const container = containerRef.current
    const canvas = canvasRef.current
    if (!container || !canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dense = container.clientWidth >= 480
    const canReact = interactive && hasFinePointer && !prefersReducedMotion

    let width = 0
    let height = 0
    let nodes: AmbientNode[] = []
    let packets: Packet[] = []
    let frameId = 0
    let linkDistance = 120
    let time = 0
    const pointer = { x: 0, y: 0, active: false }

    const namedPositions = () => {
      const cx = width * 0.52
      const cy = height * 0.5
      const scale = Math.min(width, height)
      return NAMED.map((node) => ({
        ...node,
        x: cx + Math.cos(node.angle) * scale * node.radius,
        y: cy + Math.sin(node.angle) * scale * node.radius,
      }))
    }

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = container.clientWidth
      height = container.clientHeight
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      linkDistance = Math.max(80, Math.min(140, Math.min(width, height) * 0.18))
      nodes = createNodes(width, height, dense)
      packets = Array.from({ length: dense ? 7 : 4 }, () => ({
        from: Math.floor(Math.random() * nodes.length),
        t: Math.random(),
        speed: 0.0018 + Math.random() * 0.0012,
      }))
    }

    const hitNamed = (x: number, y: number) => {
      let best: ReturnType<typeof namedPositions>[number] | null = null
      let bestDist = 22
      for (const node of namedPositions()) {
        const dist = Math.hypot(node.x - x, node.y - y)
        if (dist < bestDist) {
          bestDist = dist
          best = node
        }
      }
      return best
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      const cx = width * 0.52
      const cy = height * 0.5
      const converge = prefersReducedMotion
        ? 0.78
        : 0.62 + 0.18 * (0.5 + 0.5 * Math.sin(time * 0.00022))

      for (let i = 0; i < nodes.length; i += 1) {
        const a = nodes[i]
        if (!a) continue
        for (let j = i + 1; j < nodes.length; j += 1) {
          const b = nodes[j]
          if (!b) continue
          const dist = Math.hypot(a.x - b.x, a.y - b.y)
          if (dist >= linkDistance) continue
          ctx.strokeStyle = `rgba(${EDGE_COLOR}, ${((1 - dist / linkDistance) * 0.18).toFixed(3)})`
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(b.x, b.y)
          ctx.stroke()
        }

        const toCenter = Math.hypot(a.x - cx, a.y - cy)
        if (toCenter < Math.min(width, height) * 0.42) {
          ctx.strokeStyle = `rgba(${NODE_COLOR}, ${(0.05 * (1 - toCenter / (Math.min(width, height) * 0.42))).toFixed(3)})`
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(cx, cy)
          ctx.stroke()
        }
      }

      for (const packet of packets) {
        const from = nodes[packet.from]
        if (!from) continue
        const x = from.x + (cx - from.x) * packet.t * 0.85
        const y = from.y + (cy - from.y) * packet.t * 0.85
        ctx.beginPath()
        ctx.fillStyle = `rgba(${NODE_COLOR}, 0.55)`
        ctx.arc(x, y, 1.4, 0, Math.PI * 2)
        ctx.fill()
      }

      let nearest: AmbientNode | null = null
      let nearestDist = HOVER_RADIUS

      for (const node of nodes) {
        let proximity = 0
        if (canReact && pointer.active) {
          const dist = Math.hypot(node.x - pointer.x, node.y - pointer.y)
          if (dist < HOVER_RADIUS) {
            proximity = 1 - dist / HOVER_RADIUS
            if (dist < nearestDist) {
              nearestDist = dist
              nearest = node
            }
          }
        }
        ctx.beginPath()
        ctx.fillStyle = `rgba(${NODE_COLOR}, ${(0.28 + proximity * 0.45).toFixed(3)})`
        ctx.arc(node.x, node.y, node.r + proximity * 1.1, 0, Math.PI * 2)
        ctx.fill()
      }

      if (nearest) {
        ctx.strokeStyle = `rgba(${NODE_COLOR}, ${(0.22 * (1 - nearestDist / HOVER_RADIUS)).toFixed(3)})`
        ctx.beginPath()
        ctx.moveTo(pointer.x, pointer.y)
        ctx.lineTo(nearest.x, nearest.y)
        ctx.stroke()
      }

      const named = namedPositions()
      for (const node of named) {
        const active = hoveredRef.current?.id === node.id
        ctx.beginPath()
        ctx.strokeStyle = `rgba(${NODE_COLOR}, ${active ? 0.7 : 0.35})`
        ctx.lineWidth = 1
        ctx.moveTo(cx, cy)
        ctx.lineTo(node.x, node.y)
        ctx.stroke()

        ctx.beginPath()
        ctx.fillStyle = `rgba(8, 9, 11, 0.85)`
        ctx.strokeStyle = `rgba(${NODE_COLOR}, ${active ? 0.9 : 0.55})`
        ctx.lineWidth = active ? 1.6 : 1.15
        ctx.arc(node.x, node.y, active ? 6 : 5, 0, Math.PI * 2)
        ctx.fill()
        ctx.stroke()
      }

      ctx.beginPath()
      ctx.fillStyle = 'rgba(22, 35, 58, 0.9)'
      ctx.strokeStyle = 'rgba(75, 141, 248, 0.7)'
      ctx.lineWidth = 1.4
      ctx.arc(cx, cy, 9 * converge + 2, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
      ctx.beginPath()
      ctx.fillStyle = 'rgba(75, 141, 248, 0.95)'
      ctx.arc(cx, cy, 3.2, 0, Math.PI * 2)
      ctx.fill()
    }

    const step = () => {
      time += 16
      const cx = width * 0.52
      const cy = height * 0.5
      const converge = 0.7 + 0.16 * Math.sin(time * 0.00022)

      for (const node of nodes) {
        const tx = cx + (node.homeX - cx) * converge
        const ty = cy + (node.homeY - cy) * converge
        node.x += (tx - node.x) * 0.02 + node.vx
        node.y += (ty - node.y) * 0.02 + node.vy

        if (canReact && pointer.active) {
          const dx = pointer.x - node.x
          const dy = pointer.y - node.y
          const dist = Math.hypot(dx, dy)
          if (dist < HOVER_RADIUS && dist > 0.001) {
            const pull = (1 - dist / HOVER_RADIUS) * ATTRACT_STRENGTH
            node.x += dx * pull
            node.y += dy * pull
          }
        }
      }

      for (const packet of packets) {
        packet.t += packet.speed
        if (packet.t >= 1) {
          packet.t = 0
          packet.from = Math.floor(Math.random() * nodes.length)
        }
      }

      draw()
      frameId = window.requestAnimationFrame(step)
    }

    resize()
    draw()

    const resizeObserver = new ResizeObserver(() => {
      resize()
      draw()
    })
    resizeObserver.observe(container)

    if (!prefersReducedMotion) {
      frameId = window.requestAnimationFrame(step)
    }

    let pendingFrame = 0
    const handlePointerMove = (event: PointerEvent) => {
      if (!canReact) return
      if (pendingFrame) return
      pendingFrame = window.requestAnimationFrame(() => {
        pendingFrame = 0
        const rect = container.getBoundingClientRect()
        pointer.x = event.clientX - rect.left
        pointer.y = event.clientY - rect.top
        pointer.active =
          pointer.x >= 0 && pointer.x <= rect.width && pointer.y >= 0 && pointer.y <= rect.height
        const next = pointer.active ? hitNamed(pointer.x, pointer.y) : null
        if (next?.id !== hoveredRef.current?.id) {
          hoveredRef.current = next
          setHovered(next)
        }
        if (prefersReducedMotion) draw()
      })
    }

    const handlePointerLeave = () => {
      pointer.active = false
      if (hoveredRef.current) {
        hoveredRef.current = null
        setHovered(null)
      }
    }

    if (canReact) {
      window.addEventListener('pointermove', handlePointerMove)
      container.addEventListener('pointerleave', handlePointerLeave)
    }

    return () => {
      window.cancelAnimationFrame(frameId)
      if (pendingFrame) window.cancelAnimationFrame(pendingFrame)
      resizeObserver.disconnect()
      if (canReact) {
        window.removeEventListener('pointermove', handlePointerMove)
        container.removeEventListener('pointerleave', handlePointerLeave)
      }
    }
  }, [hasFinePointer, interactive, prefersReducedMotion])

  return (
    <div ref={containerRef} className={cn('relative h-full w-full overflow-hidden', className)}>
      <div className="grid-texture-animated pointer-events-none absolute inset-0 opacity-30" />
      <canvas ref={canvasRef} className="absolute inset-0" />
      {hovered ? (
        <div
          className="pointer-events-none absolute top-24 right-8 rounded-md border border-line-strong bg-surface/80 px-3 py-2 backdrop-blur-sm"
          role="status"
        >
          <p className="text-xs font-semibold text-ink">{hovered.label}</p>
          <p className="mt-0.5 text-2xs text-ink-faint">{hovered.detail}</p>
        </div>
      ) : null}
    </div>
  )
}
