import { useEffect, useRef } from 'react'

import { usePrefersReducedMotion } from '@/hooks/usePrefersReducedMotion'
import { backdropState } from './backdropIntensity'

interface Node {
  x: number
  y: number
  vx: number
  vy: number
  r: number
}

const NODE_COLOR = '75, 141, 248' // --color-accent
const EDGE_COLOR = '106, 114, 125' // --color-ink-faint
const HOVER_RADIUS = 150
const ATTRACT_STRENGTH = 0.002
const EASE = 0.035

function createNodes(width: number, height: number, dense: boolean): Node[] {
  const cap = dense ? 90 : 32
  const min = dense ? 42 : 16
  const count = Math.max(min, Math.min(cap, Math.round((width * height) / 22000)))

  return Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.15,
    vy: (Math.random() - 0.5) * 0.15,
    r: Math.random() * 1.2 + 0.8,
  }))
}

/**
 * A single ambient node/edge network fixed behind the entire landing page
 * (not per-section) — the "continuous environment" the page scrolls
 * through. Sections call `useBackdropZone` to raise or lower its energy as
 * they come into view; this component just eases toward whatever target is
 * currently set and reacts to the pointer on top of that.
 *
 * Mount once, at the page root. Pure canvas + rAF, no dependency. Pauses
 * entirely under `prefers-reduced-motion` (a single static frame is drawn
 * instead) and runs a lighter node count with no pointer interaction on
 * touch/small viewports.
 */
export function LandingBackdrop() {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const prefersReducedMotion = usePrefersReducedMotion()

  useEffect(() => {
    const container = containerRef.current
    const canvas = canvasRef.current
    if (!container || !canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const hasFinePointer = window.matchMedia('(pointer: fine)').matches
    const isSmallViewport = window.matchMedia('(max-width: 640px)').matches
    const dense = !isSmallViewport
    const canReact = hasFinePointer && !prefersReducedMotion

    let width = 0
    let height = 0
    let nodes: Node[] = []
    let frameId = 0
    let linkDistance = 150
    let currentIntensity = backdropState.target
    const pointer = { x: 0, y: 0, active: false }

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      linkDistance = Math.max(110, Math.min(190, Math.min(width, height) * 0.18))
      nodes = createNodes(width, height, dense)
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      const energy = 0.32 + currentIntensity * 0.68

      for (let i = 0; i < nodes.length; i += 1) {
        const a = nodes[i]
        if (!a) continue
        for (let j = i + 1; j < nodes.length; j += 1) {
          const b = nodes[j]
          if (!b) continue
          const dx = a.x - b.x
          const dy = a.y - b.y
          const dist = Math.hypot(dx, dy)
          if (dist >= linkDistance) continue

          const opacity = (1 - dist / linkDistance) * 0.26 * energy
          ctx.strokeStyle = `rgba(${EDGE_COLOR}, ${opacity.toFixed(3)})`
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(b.x, b.y)
          ctx.stroke()
        }
      }

      let nearest: Node | null = null
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

        const opacity = (0.38 + proximity * 0.5) * energy
        const radius = node.r + proximity * 1.4
        ctx.beginPath()
        ctx.fillStyle = `rgba(${NODE_COLOR}, ${opacity.toFixed(3)})`
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2)
        ctx.fill()
      }

      if (nearest) {
        const lineOpacity = 0.32 * (1 - nearestDist / HOVER_RADIUS) * energy
        ctx.strokeStyle = `rgba(${NODE_COLOR}, ${lineOpacity.toFixed(3)})`
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(pointer.x, pointer.y)
        ctx.lineTo(nearest.x, nearest.y)
        ctx.stroke()
      }
    }

    const step = () => {
      currentIntensity += (backdropState.target - currentIntensity) * EASE

      for (const node of nodes) {
        node.x += node.vx
        node.y += node.vy

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

        if (node.x <= 0 || node.x >= width) node.vx *= -1
        if (node.y <= 0 || node.y >= height) node.vy *= -1
        node.x = Math.min(Math.max(node.x, 0), width)
        node.y = Math.min(Math.max(node.y, 0), height)
      }

      draw()
      frameId = window.requestAnimationFrame(step)
    }

    resize()
    draw()

    let resizeTimer = 0
    const handleResize = () => {
      window.clearTimeout(resizeTimer)
      resizeTimer = window.setTimeout(() => {
        resize()
        draw()
      }, 150)
    }
    window.addEventListener('resize', handleResize)

    if (!prefersReducedMotion) {
      frameId = window.requestAnimationFrame(step)
    }

    let pendingFrame = 0
    const handlePointerMove = (event: PointerEvent) => {
      if (pendingFrame) return
      pendingFrame = window.requestAnimationFrame(() => {
        pendingFrame = 0
        pointer.x = event.clientX
        pointer.y = event.clientY
        pointer.active = true
        if (prefersReducedMotion) draw()
      })
    }
    const handlePointerLeave = () => {
      pointer.active = false
    }

    if (canReact) {
      window.addEventListener('pointermove', handlePointerMove)
      document.documentElement.addEventListener('pointerleave', handlePointerLeave)
    }

    return () => {
      window.cancelAnimationFrame(frameId)
      if (pendingFrame) window.cancelAnimationFrame(pendingFrame)
      window.clearTimeout(resizeTimer)
      window.removeEventListener('resize', handleResize)
      if (canReact) {
        window.removeEventListener('pointermove', handlePointerMove)
        document.documentElement.removeEventListener('pointerleave', handlePointerLeave)
      }
    }
  }, [prefersReducedMotion])

  return (
    <div ref={containerRef} aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="grid-texture-animated absolute inset-0 opacity-50" />
      <canvas ref={canvasRef} className="absolute inset-0" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_78%_58%_at_50%_0%,transparent_0%,rgba(8,9,11,0.5)_78%)]" />
    </div>
  )
}
