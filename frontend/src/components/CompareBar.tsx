'use client'

import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { INK, POP } from '@/lib/pop'

interface Props {
  label: string
  aValue: number
  bValue: number
  aName: string
  bName: string
}

export default function CompareBar({ label, aValue, bValue, aName, bName }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-40px' })

  const max = Math.max(aValue, bValue, 1)
  const aPct = (aValue / max) * 100
  const bPct = (bValue / max) * 100
  const aWins = aValue >= bValue

  return (
    <div ref={ref}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-bold uppercase tracking-widest" style={{ color: INK }}>
          {label}
        </span>
        <div className="flex gap-4 text-xs tabular-nums font-bold">
          <span style={{ color: aWins ? POP.red : '#57534e' }}>
            {aValue.toFixed(1)}
          </span>
          <span style={{ color: !aWins ? POP.blue : '#57534e' }}>
            {bValue.toFixed(1)}
          </span>
        </div>
      </div>
      <div className="flex gap-1 h-2.5">
        <div
          className="flex-1 flex justify-end overflow-hidden"
          style={{ background: '#e7e2d6', border: '1.5px solid ' + INK }}
        >
          <motion.div
            className="h-full"
            style={{ background: POP.red }}
            initial={{ width: 0 }}
            animate={inView ? { width: `${aPct}%` } : { width: 0 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>
        <div
          className="flex-1 overflow-hidden"
          style={{ background: '#e7e2d6', border: '1.5px solid ' + INK }}
        >
          <motion.div
            className="h-full"
            style={{ background: POP.blue }}
            initial={{ width: 0 }}
            animate={inView ? { width: `${bPct}%` } : { width: 0 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
          />
        </div>
      </div>
    </div>
  )
}
