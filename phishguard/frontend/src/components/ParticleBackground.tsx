import { useEffect, useRef } from 'react'
import { DURATIONS } from '../theme'

interface Particle {
  x: number      // current x in canvas pixels
  y: number      // current y in canvas pixels
  vx: number     // velocity x
  vy: number     // velocity y
  radius: number // 1–2 px
  alpha: number  // 0.04–0.08
}

function randomBetween(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

function initParticles(W: number, H: number): Particle[] {
  const count = Math.floor((W * H) / 12000)
  const particles: Particle[] = []
  for (let i = 0; i < count; i++) {
    const speed = randomBetween(DURATIONS.particleMin, DURATIONS.particleMax)
    const angle = Math.random() * 2 * Math.PI
    particles.push({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      radius: randomBetween(1, 2),
      alpha: randomBetween(0.04, 0.08),
    })
  }
  return particles
}

function drawFrame(
  ctx: CanvasRenderingContext2D,
  particles: Particle[],
  W: number,
  H: number,
): void {
  ctx.clearRect(0, 0, W, H)
  for (const p of particles) {
    p.x += p.vx
    p.y += p.vy
    // Wrap edges
    if (p.x < 0) p.x = W
    if (p.x > W) p.x = 0
    if (p.y < 0) p.y = H
    if (p.y > H) p.y = 0
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.radius, 0, 2 * Math.PI)
    ctx.fillStyle = `rgba(0, 229, 255, ${p.alpha})`
    ctx.fill()
  }
}

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafIdRef = useRef<number>(0)
  const particlesRef = useRef<Particle[]>([])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches

    // Set canvas dimensions to match physical pixels
    const W = canvas.offsetWidth || window.innerWidth
    const H = canvas.offsetHeight || window.innerHeight
    canvas.width = W
    canvas.height = H

    particlesRef.current = initParticles(W, H)

    if (prefersReducedMotion) {
      // Draw one static frame only — no RAF loop
      drawFrame(ctx, particlesRef.current, W, H)
      return
    }

    function loop() {
      if (!canvas || !ctx) return
      drawFrame(ctx, particlesRef.current, canvas.width, canvas.height)
      rafIdRef.current = requestAnimationFrame(loop)
    }

    rafIdRef.current = requestAnimationFrame(loop)

    // Pause/resume on page visibility changes
    const handleVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(rafIdRef.current)
      } else {
        rafIdRef.current = requestAnimationFrame(loop)
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)

    // Resize: reset canvas dimensions and reinitialise particles
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (!canvas || !ctx) return
        canvas.width = Math.round(width)
        canvas.height = Math.round(height)
        particlesRef.current = initParticles(canvas.width, canvas.height)
      }
    })
    resizeObserver.observe(canvas)

    return () => {
      cancelAnimationFrame(rafIdRef.current)
      document.removeEventListener('visibilitychange', handleVisibility)
      resizeObserver.disconnect()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: -1,
        pointerEvents: 'none',
      }}
    />
  )
}
