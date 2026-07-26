'use client'

import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { cn } from '@/lib/utils'

interface Props {
  children: React.ReactNode
  className?: string
  delay?: number
  direction?: 'up' | 'left' | 'none'
}

export default function AnimatedSection({ children, className, delay = 0, direction = 'up' }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  const initial =
    direction === 'up' ? { opacity: 0, y: 40 } :
    direction === 'left' ? { opacity: 0, x: -30 } :
    { opacity: 0 }

  return (
    <motion.div
      ref={ref}
      initial={initial}
      animate={inView ? { opacity: 1, y: 0, x: 0 } : initial}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={cn(className)}
    >
      {children}
    </motion.div>
  )
}
