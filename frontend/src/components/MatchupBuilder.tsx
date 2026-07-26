'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { INK, POP, hard, TIER_COLOR } from '@/lib/pop'

const EXPO = [0.16, 1, 0.3, 1] as [number, number, number, number]
const SPRING = { type: 'spring' as const, stiffness: 80, damping: 13 }

interface Opt {
  name: string
  division: string | null
}

interface PredictResult {
  error?: string
  probA: number
  probB: number
  tier: string
  predicted_winner: string
  note: string
  a: { name: string; division: string | null; record: string }
  b: { name: string; division: string | null; record: string }
  factors: { key: string; a: number; b: number; edge: number }[]
}

export default function MatchupBuilder({ fighters }: { fighters: Opt[] }) {
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PredictResult | null>(null)

  async function run() {
    setError(null)
    if (!a.trim() || !b.trim()) { setError('Pick two fighters.'); return }
    if (a.trim().toLowerCase() === b.trim().toLowerCase()) { setError('Pick two different fighters.'); return }
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ a: a.trim(), b: b.trim() }),
      })
      const json: PredictResult = await res.json()
      if (!res.ok || json.error) { setError(json.error ?? 'Prediction failed.'); return }
      setResult(json)
    } catch {
      setError('Network error — is the dev server running?')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = { border: `3px solid ${INK}`, ...hard(INK, 5, 5) }

  return (
    <div>
      {/* Picker */}
      <div className="grid md:grid-cols-[1fr_auto_1fr] gap-6 items-center">
        <div>
          <label className="block text-[11px] tracking-widest uppercase font-bold mb-2" style={{ color: POP.red }}>Fighter A</label>
          <input
            list="fighters-list"
            value={a}
            onChange={(e) => setA(e.target.value)}
            placeholder="Type a name…"
            className="w-full bg-white px-4 py-3 text-base font-bold outline-none"
            style={inputStyle}
          />
        </div>

        <div className="text-center font-bold px-2 pt-6" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(32px,5vw,56px)', color: POP.magenta, WebkitTextStroke: `2px ${INK}` }}>
          VS
        </div>

        <div>
          <label className="block text-[11px] tracking-widest uppercase font-bold mb-2" style={{ color: POP.blue }}>Fighter B</label>
          <input
            list="fighters-list"
            value={b}
            onChange={(e) => setB(e.target.value)}
            placeholder="Type a name…"
            className="w-full bg-white px-4 py-3 text-base font-bold outline-none"
            style={inputStyle}
          />
        </div>
      </div>

      <datalist id="fighters-list">
        {fighters.map((f) => (
          <option key={f.name} value={f.name}>{f.division ?? ''}</option>
        ))}
      </datalist>

      <div className="mt-8 flex items-center gap-4">
        <button
          onClick={run}
          disabled={loading}
          className="text-sm font-bold tracking-widest uppercase px-8 py-4 text-white transition-transform hover:scale-105 disabled:opacity-60"
          style={{ background: INK, ...hard(POP.magenta, 6, 6) }}
        >
          {loading ? 'Calculating…' : 'Predict fight →'}
        </button>
        {error && <span className="text-sm font-bold" style={{ color: POP.redDeep }}>{error}</span>}
      </div>

      {/* Result */}
      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            key={result.a.name + result.b.name}
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ ...SPRING }}
            className="mt-12 bg-white p-8"
            style={{ border: `3px solid ${INK}`, ...hard(INK, 8, 8) }}
          >
            {/* Winner banner */}
            <motion.div initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ ...SPRING, delay: 0.1 }}
              className="inline-flex items-center gap-2 px-4 py-1.5 mb-6 text-white text-xs font-bold tracking-widest uppercase"
              style={{ background: TIER_COLOR[result.tier] ?? INK }}>
              {result.tier} confidence · Pick: {result.predicted_winner}
            </motion.div>

            {/* Names + probabilities */}
            <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center mb-6">
              <div>
                <div className="font-bold uppercase leading-tight" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(18px,2.5vw,30px)', color: POP.red }}>{result.a.name}</div>
                <div className="text-[11px] tracking-widest uppercase font-bold mt-1" style={{ color: '#57534e' }}>{result.a.division} · {result.a.record}</div>
                <div className="tabular-nums font-bold mt-2" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(36px,6vw,64px)', color: INK }}>{(result.probA * 100).toFixed(0)}%</div>
              </div>
              <div className="font-bold" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(24px,4vw,44px)', color: POP.magenta, WebkitTextStroke: `2px ${INK}` }}>VS</div>
              <div className="text-right">
                <div className="font-bold uppercase leading-tight" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(18px,2.5vw,30px)', color: POP.blue }}>{result.b.name}</div>
                <div className="text-[11px] tracking-widest uppercase font-bold mt-1" style={{ color: '#57534e' }}>{result.b.division} · {result.b.record}</div>
                <div className="tabular-nums font-bold mt-2" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(36px,6vw,64px)', color: INK }}>{(result.probB * 100).toFixed(0)}%</div>
              </div>
            </div>

            {/* Split bar */}
            <div className="h-[14px] flex overflow-hidden mb-8" style={{ border: `2px solid ${INK}` }}>
              <motion.div className="h-full" style={{ background: POP.red }} initial={{ width: 0 }} animate={{ width: `${result.probA * 100}%` }} transition={{ duration: 0.9, ease: EXPO }} />
              <motion.div className="h-full" style={{ background: POP.blue }} initial={{ width: 0 }} animate={{ width: `${result.probB * 100}%` }} transition={{ duration: 0.9, ease: EXPO }} />
            </div>

            {/* Factor breakdown */}
            <div className="grid sm:grid-cols-2 gap-4">
              {result.factors.map((f, i) => (
                <motion.div key={f.key} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 + i * 0.06 }}
                  className="p-3" style={{ border: `2px solid ${INK}`, background: '#faf6ec' }}>
                  <div className="flex justify-between text-[11px] tracking-widest uppercase font-bold mb-1" style={{ color: '#57534e' }}>
                    <span style={{ color: INK }}>{f.a}</span>
                    <span>{f.key}</span>
                    <span style={{ color: INK }}>{f.b}</span>
                  </div>
                  <div className="h-[6px] flex overflow-hidden" style={{ border: `1.5px solid ${INK}` }}>
                    <div className="h-full" style={{ background: POP.red, width: `${f.edge * 100}%` }} />
                    <div className="h-full" style={{ background: POP.blue, width: `${(1 - f.edge) * 100}%` }} />
                  </div>
                </motion.div>
              ))}
            </div>

            <p className="text-[11px] mt-6" style={{ color: '#78716c' }}>{result.note}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
