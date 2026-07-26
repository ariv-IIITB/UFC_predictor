'use client'

import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

const SPRING = { type: 'spring' as const, stiffness: 80, damping: 13 }

export default function Reveal({
  children,
  delay = 0,
  y = 40,
  x = 0,
  rotate = 0,
  scale = 1,
  className = '',
  once = true,
}: {
  children: ReactNode
  delay?: number
  y?: number
  x?: number
  rotate?: number
  scale?: number
  className?: string
  once?: boolean
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y, x, rotate, scale: scale === 1 ? 0.94 : scale }}
      whileInView={{ opacity: 1, y: 0, x: 0, rotate: 0, scale: 1 }}
      viewport={{ once, margin: '-60px 0px' }}
      transition={{ ...SPRING, delay }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
