'use client'

import { motion } from 'framer-motion'
import { INK, hard, type PageTheme } from '@/lib/pop'

const EXPO = [0.16, 1, 0.3, 1] as [number, number, number, number]

export default function PopHeader({
  label,
  title,
  th,
  align = 'left',
}: {
  label: string
  title: string
  th: PageTheme
  align?: 'left' | 'center'
}) {
  return (
    <div className={align === 'center' ? 'text-center' : ''}>
      <motion.div
        initial={{ opacity: 0, x: align === 'center' ? 0 : -24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className={`inline-flex items-center gap-3 mb-5 px-3 py-1 ${align === 'center' ? 'justify-center' : ''}`}
        style={{ background: th.accent, ...hard(th.tone === 'dark' ? '#fff' : INK, 4, 4) }}
      >
        <span
          className="text-xs tracking-[0.3em] uppercase font-bold"
          style={{ color: th.tone === 'light' ? '#fff' : INK }}
        >
          {label}
        </span>
      </motion.div>
      <motion.h1
        initial={{ clipPath: 'inset(0 0 100% 0)', y: 50, skewY: 4 }}
        animate={{ clipPath: 'inset(0 0 0% 0)', y: 0, skewY: 0 }}
        transition={{ duration: 0.9, ease: EXPO }}
        className="font-bold leading-[0.8] tracking-tighter uppercase"
        style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontSize: 'clamp(48px, 10vw, 128px)',
          color: th.text,
        }}
      >
        {title}
      </motion.h1>
    </div>
  )
}
