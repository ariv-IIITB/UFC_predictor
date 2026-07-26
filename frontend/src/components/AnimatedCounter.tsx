'use client'

import { useEffect, useRef, useState } from 'react'
import { useInView } from 'framer-motion'

interface Props {
  value: number
  decimals?: number
  prefix?: string
  suffix?: string
  duration?: number
}

export default function AnimatedCounter({ value, decimals = 0, prefix = '', suffix = '', duration = 1800 }: Props) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  const [display, setDisplay] = useState(0)
  const started = useRef(false)

  useEffect(() => {
    if (!inView || started.current) return
    started.current = true

    const start = performance.now()
    const from = 0

    function step(now: number) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(from + (value - from) * eased)
      if (progress < 1) requestAnimationFrame(step)
    }

    requestAnimationFrame(step)
  }, [inView, value, duration])

  return (
    <span ref={ref}>
      {prefix}{display.toFixed(decimals)}{suffix}
    </span>
  )
}
