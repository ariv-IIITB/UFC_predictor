'use client'

import { useEffect, useState } from 'react'
import { getCountdown } from '@/lib/utils'

interface Props {
  target: string
  eventName?: string | null
  accent?: string
  tone?: 'light' | 'dark' // background tone the countdown sits on
}

export default function Countdown({ target, eventName, accent = '#ff2e4d', tone = 'dark' }: Props) {
  // Start as null on both server and the client's first render so the two match exactly.
  // The real, time-dependent value is only computed after mount (client-only), avoiding
  // a hydration mismatch (Date.now() would otherwise differ between server-render time
  // and client-hydrate time by a second or more).
  const [tick, setTick] = useState<ReturnType<typeof getCountdown> | null>(null)

  useEffect(() => {
    setTick(getCountdown(target))
    const id = setInterval(() => setTick(getCountdown(target)), 1000)
    return () => clearInterval(id)
  }, [target])

  const numColor = tone === 'light' ? '#0a0a0c' : '#fafafa'
  const labelColor = tone === 'light' ? 'rgba(10,10,12,0.55)' : '#a1a1aa'

  if (!tick) {
    // Matches the server-rendered placeholder exactly; swapped for real numbers post-mount.
    return (
      <div className="flex gap-4">
        {['Days', 'Hrs', 'Min', 'Sec'].map((label) => (
          <div key={label} className="text-center">
            <div
              className="text-5xl font-display font-bold tabular-nums"
              style={{ fontFamily: "'Space Grotesk', sans-serif", minWidth: '2.5ch', color: numColor }}
            >
              --
            </div>
            <div className="text-[10px] tracking-widest uppercase mt-1" style={{ color: labelColor }}>{label}</div>
          </div>
        ))}
      </div>
    )
  }

  if (tick.past) {
    return (
      <div className="text-sm tracking-widest uppercase" style={{ color: labelColor }}>
        Event in progress or completed
      </div>
    )
  }

  const units = [
    { label: 'Days', value: tick.days },
    { label: 'Hrs', value: tick.hours },
    { label: 'Min', value: tick.minutes },
    { label: 'Sec', value: tick.seconds },
  ]

  return (
    <div className="space-y-3">
      {eventName && (
        <p className="text-xs tracking-widest uppercase font-bold" style={{ color: accent }}>
          Next — {eventName}
        </p>
      )}
      <div className="flex gap-4">
        {units.map(({ label, value }) => (
          <div key={label} className="text-center">
            <div
              className="text-5xl font-display font-bold tabular-nums"
              style={{ fontFamily: "'Space Grotesk', sans-serif", minWidth: '2.5ch', color: numColor }}
            >
              {String(value).padStart(2, '0')}
            </div>
            <div className="text-[10px] tracking-widest uppercase mt-1" style={{ color: labelColor }}>{label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
