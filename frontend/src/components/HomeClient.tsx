'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useRef } from 'react'
import { motion, useInView, useScroll, useTransform, type MotionValue } from 'framer-motion'
import AnimatedCounter from '@/components/AnimatedCounter'
import Countdown from '@/components/Countdown'
import { fmtDate } from '@/lib/utils'
import summary from '@/lib/summary.json'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface RecentPrediction {
  fight_id_manual: string
  event_name: string | null
  fight_date: string | null
  fighter_a: string | null
  fighter_b: string | null
  predicted_winner: string | null
  a_win_probability: number | null
  b_win_probability: number | null
  confidence_tier: string | null
  division_norm: string | null
}
export interface RecentFight {
  fight_id: string
  event_name: string | null
  fight_date: string | null
  fighter_a: string | null
  fighter_b: string | null
  winner: string | null
  method: string | null
  division: string | null
}
export interface TopFighter {
  fighter_id: string
  fighter_name: string | null
  overall_rating: number | null
  elo_rating: number | null
  wins: number | null
  losses: number | null
  win_rate: number | null
  division: string | null
  striking_offense: number | null
  grappling_offense: number | null
  conditioning_score: number | null
  takedown_offense: number | null
  momentum_score: number | null
}
export interface HomeClientProps {
  nextEvent: { event_name: string | null; fight_date: string | null } | null
  predictions: RecentPrediction[]
  recentFights: RecentFight[]
  topFighters: TopFighter[]
}

// ─── Pop-art comic-panel theme system ─────────────────────────────────────────

const EXPO = [0.16, 1, 0.3, 1] as [number, number, number, number]
const INK = '#0a0a0c'
const SPRING = { type: 'spring' as const, stiffness: 80, damping: 13 }
const hard = (c = INK, x = 8, y = 8) => ({ boxShadow: `${x}px ${y}px 0 ${c}` })

interface Theme {
  bg: string
  text: string
  sub: string
  accent: string
  accent2: string
  tone: 'light' | 'dark'
}

const T = {
  hero: { bg: '#f4ead6', text: INK, sub: '#57534e', accent: '#ff2e4d', accent2: '#1a5fd4', tone: 'light' },
  predictions: { bg: '#1a5fd4', text: '#ffffff', sub: 'rgba(255,255,255,0.72)', accent: '#ffd400', accent2: '#ff2e4d', tone: 'dark' },
  history: { bg: '#ffd400', text: INK, sub: 'rgba(10,10,12,0.6)', accent: '#e01e37', accent2: '#1a5fd4', tone: 'light' },
  matchups: { bg: '#e01e37', text: '#fff3e6', sub: 'rgba(255,243,230,0.78)', accent: '#ffd400', accent2: '#1a5fd4', tone: 'dark' },
  fighters: { bg: '#0fb890', text: INK, sub: 'rgba(10,10,12,0.62)', accent: INK, accent2: '#e01e37', tone: 'light' },
  model: { bg: '#ff6a00', text: INK, sub: 'rgba(10,10,12,0.66)', accent: INK, accent2: '#e01e37', tone: 'light' },
} satisfies Record<string, Theme>

const TIER_COLOR: Record<string, string> = { High: '#ff2e4d', Medium: '#ff6a00', Low: '#71717a' }

// ─── Bold section heading — huge, clip-reveal + skew ─────────────────────────

function SectionHead({ label, title, th, isInView, align = 'left' }: {
  label: string; title: string; th: Theme; isInView: boolean; align?: 'left' | 'center'
}) {
  return (
    <div className={align === 'center' ? 'text-center' : ''}>
      <motion.div
        initial={{ opacity: 0, x: align === 'center' ? 0 : -24 }}
        animate={isInView ? { opacity: 1, x: 0 } : {}}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className={`inline-flex items-center gap-3 mb-5 px-3 py-1 ${align === 'center' ? 'justify-center' : ''}`}
        style={{ background: th.accent, ...hard(th.text, 4, 4) }}
      >
        <span className="text-xs tracking-[0.3em] uppercase font-bold" style={{ color: th.tone === 'light' ? '#fff' : INK }}>
          {label}
        </span>
      </motion.div>
      <motion.h2
        initial={{ clipPath: 'inset(0 0 100% 0)', y: 60, skewY: 4 }}
        animate={isInView ? { clipPath: 'inset(0 0 0% 0)', y: 0, skewY: 0 } : {}}
        transition={{ duration: 1, ease: EXPO }}
        className="font-bold leading-[0.8] tracking-tighter uppercase"
        style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(56px, 12vw, 150px)', color: th.text }}
      >
        {title}
      </motion.h2>
    </div>
  )
}

// ─── Featured portrait — dramatic entrance + parallax, framed poster ─────────

function PopPortrait({ src, th, scrollY, rotate = -6, className = '', priority = false }: {
  src: string; th: Theme; scrollY: MotionValue<string>; rotate?: number; className?: string; priority?: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px 0px' })
  return (
    <div ref={ref} className={`relative ${className}`}>
      <div className="halftone-lg absolute inset-0 -z-10 translate-x-5 translate-y-5" style={{ color: th.accent }} />
      <div className="absolute inset-0 -z-10 -translate-x-4 -translate-y-4" style={{ background: th.accent2 }} />
      <motion.div
        style={{ y: scrollY, border: `4px solid ${INK}` }}
        initial={{ opacity: 0, scale: 0.65, rotate }}
        animate={isInView ? { opacity: 1, scale: 1, rotate: rotate / 2 } : {}}
        transition={{ ...SPRING, stiffness: 65 }}
        className="relative aspect-[5/7] overflow-hidden"
      >
        <Image src={src} fill alt="" priority={priority} className="object-cover object-center" sizes="(max-width:768px) 80vw, 380px" />
      </motion.div>
    </div>
  )
}

// ─── §2 PREDICTIONS (blue) ────────────────────────────────────────────────────

function PredictionsSection({ predictions }: { predictions: RecentPrediction[] }) {
  const th = T.predictions
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px 0px' })
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const imgY = useTransform(scrollYProgress, [0, 1], ['22%', '-22%'])
  const event = predictions[0]?.event_name ?? null
  const date = predictions[0]?.fight_date ?? null

  return (
    <section id="predictions" ref={ref} className="relative px-6 py-28 overflow-hidden scroll-mt-14" style={{ background: th.bg, borderTop: `5px solid ${INK}` }}>
      <div className="halftone absolute inset-0 opacity-[0.08] pointer-events-none" style={{ color: '#fff' }} />
      <div className="mx-auto max-w-7xl grid lg:grid-cols-[1fr_auto] gap-16 items-start relative z-10">
        <div className="min-w-0">
          <SectionHead label={event ? `${event} · ${fmtDate(date)}` : 'Upcoming card'} title="PREDICTIONS" th={th} isInView={isInView} />
          <div className="grid sm:grid-cols-2 gap-5 mt-12">
            {predictions.slice(0, 6).map((p, i) => {
              const maxProb = Math.max(p.a_win_probability ?? 0, p.b_win_probability ?? 0)
              return (
                <motion.div
                  key={p.fight_id_manual}
                  initial={{ opacity: 0, y: 60, scale: 0.85, rotate: i % 2 ? 3 : -3 }}
                  animate={isInView ? { opacity: 1, y: 0, scale: 1, rotate: 0 } : {}}
                  transition={{ ...SPRING, delay: 0.1 + i * 0.08 }}
                  className="p-5 bg-white"
                  style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] tracking-widest uppercase font-bold" style={{ color: '#57534e' }}>{p.division_norm ?? '—'}</span>
                    {p.confidence_tier && (
                      <span className="text-[10px] tracking-widest uppercase font-bold px-2 py-0.5 text-white" style={{ background: TIER_COLOR[p.confidence_tier] ?? '#71717a' }}>
                        {p.confidence_tier}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-base font-bold truncate" style={{ color: INK }}>{p.fighter_a}</span>
                    <span className="text-[10px] text-[#a1a1aa] shrink-0">vs</span>
                    <span className="text-base font-bold truncate" style={{ color: INK }}>{p.fighter_b}</span>
                  </div>
                  {p.predicted_winner && (
                    <>
                      <div className="text-xs mb-2" style={{ color: '#57534e' }}>
                        Pick: <span className="font-bold" style={{ color: '#1a5fd4' }}>{p.predicted_winner}</span>
                        {maxProb > 0 && <span className="ml-2 font-bold" style={{ color: INK }}>{(maxProb * 100).toFixed(0)}%</span>}
                      </div>
                      <div className="h-[6px] overflow-hidden" style={{ background: '#e7e2d6', border: `1.5px solid ${INK}` }}>
                        <motion.div className="h-full origin-left" style={{ background: th.accent, width: `${maxProb * 100}%` }}
                          initial={{ scaleX: 0 }} animate={isInView ? { scaleX: 1 } : {}} transition={{ duration: 0.9, delay: 0.35 + i * 0.07, ease: EXPO }} />
                      </div>
                    </>
                  )}
                </motion.div>
              )
            })}
          </div>
          <Link href="/predict" className="inline-block mt-8 text-xs tracking-widest uppercase font-bold px-5 py-3" style={{ background: th.accent, color: INK, ...hard(INK, 5, 5) }}>Full card →</Link>
        </div>
        <PopPortrait src="/fighters/f3.avif" th={th} scrollY={imgY} rotate={6} className="hidden lg:block w-[280px] xl:w-[360px] mt-10" />
      </div>
    </section>
  )
}

// ─── §3 FIGHT HISTORY (yellow) ───────────────────────────────────────────────

function FightHistorySection({ fights }: { fights: RecentFight[] }) {
  const th = T.history
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px 0px' })
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const imgY = useTransform(scrollYProgress, [0, 1], ['22%', '-22%'])

  return (
    <section id="history" ref={ref} className="relative px-6 py-28 overflow-hidden scroll-mt-14" style={{ background: th.bg, borderTop: `5px solid ${INK}` }}>
      <div className="halftone absolute inset-0 opacity-[0.06] pointer-events-none" style={{ color: INK }} />
      <div className="mx-auto max-w-7xl grid lg:grid-cols-[auto_1fr] gap-16 items-start relative z-10">
        <PopPortrait src="/fighters/f5.avif" th={th} scrollY={imgY} rotate={-6} className="hidden lg:block w-[280px] xl:w-[360px] mt-10" />
        <div className="min-w-0">
          <SectionHead label="Results database" title="FIGHTS" th={th} isInView={isInView} />
          <div className="space-y-3 mt-12">
{fights.map((f, i) => {
              const aWon = f.winner && f.fighter_a && f.winner.toLowerCase().includes(f.fighter_a.split(' ').slice(-1)[0].toLowerCase())
              return (
                <motion.div
                  key={f.fight_id}
                  initial={{ opacity: 0, x: 80, rotate: 2 }}
                  animate={isInView ? { opacity: 1, x: 0, rotate: 0 } : {}}
                  transition={{ ...SPRING, delay: 0.05 + i * 0.06 }}
                  className="flex items-center gap-4 py-3 px-4 bg-white"
                  style={{ border: `3px solid ${INK}`, ...hard(INK, 5, 5) }}
                >
                  <div className="text-[10px] tracking-widest uppercase font-bold w-20 shrink-0 hidden sm:block" style={{ color: '#78716c' }}>{fmtDate(f.fight_date)}</div>
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="text-sm font-bold truncate" style={{ color: aWon ? INK : '#a8a29e' }}>{f.fighter_a}</span>
                    <span className="text-[10px] shrink-0" style={{ color: '#a8a29e' }}>vs</span>
                    <span className="text-sm font-bold truncate" style={{ color: !aWon && f.winner ? INK : '#a8a29e' }}>{f.fighter_b}</span>
                  </div>
                  <div className="shrink-0 text-right hidden sm:block">
                    <div className="text-xs font-bold px-2 py-0.5 text-white inline-block" style={{ background: th.accent }}>{f.winner?.split(' ').slice(-1)[0]}</div>
                    <div className="text-[10px] uppercase tracking-wide mt-0.5" style={{ color: '#78716c' }}>{f.method}</div>
                  </div>
                </motion.div>
              )
            })}
          </div>
          <Link href="/fights" className="inline-block mt-8 text-xs tracking-widest uppercase font-bold px-5 py-3 text-white" style={{ background: th.accent, ...hard(INK, 5, 5) }}>All fights →</Link>
        </div>
      </div>
    </section>
  )
}

// ─── §4 FIGHTERS (teal) ───────────────────────────────────────────────────────

function FightersSection({ fighters }: { fighters: TopFighter[] }) {
  const th = T.fighters
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px 0px' })
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const imgY = useTransform(scrollYProgress, [0, 1], ['22%', '-22%'])

  return (
    <section id="fighters" ref={ref} className="relative px-6 py-28 overflow-hidden scroll-mt-14" style={{ background: th.bg, borderTop: `5px solid ${INK}` }}>
      <div className="halftone absolute inset-0 opacity-[0.06] pointer-events-none" style={{ color: INK }} />
      <div className="mx-auto max-w-7xl grid lg:grid-cols-[1fr_auto] gap-16 items-start relative z-10">
        <div className="min-w-0">
          <SectionHead label="Ranked by ELO" title="FIGHTERS" th={th} isInView={isInView} />
          <div className="space-y-3 mt-12">
            {fighters.slice(0, 8).map((f, i) => (
              <motion.div key={f.fighter_id} initial={{ opacity: 0, y: 40, scale: 0.9 }} animate={isInView ? { opacity: 1, y: 0, scale: 1 } : {}} transition={{ ...SPRING, delay: 0.05 + i * 0.06 }}>
                <Link href={`/fighters/${f.fighter_id}`} className="flex items-center gap-5 py-3 px-4 bg-white transition-transform hover:-translate-y-0.5" style={{ border: `3px solid ${INK}`, ...hard(INK, 5, 5) }}>
                  <span className="font-bold w-9 shrink-0 tabular-nums text-center text-white" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '14px', background: i === 0 ? th.accent2 : INK, padding: '2px 0' }}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-base font-bold truncate" style={{ color: INK }}>{f.fighter_name}</div>
                    <div className="text-[10px] tracking-widest uppercase mt-0.5" style={{ color: '#57534e' }}>{f.division}</div>
                  </div>
                  <div className="tabular-nums font-bold shrink-0" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '26px', color: th.accent2 }}>{f.elo_rating?.toFixed(0) ?? '—'}</div>
                  <div className="text-xs font-bold shrink-0 hidden sm:block" style={{ color: '#57534e' }}>{f.wins ?? 0}–{f.losses ?? 0}</div>
                  <div className="text-xs shrink-0 hidden md:block tabular-nums" style={{ color: '#78716c' }}>{f.overall_rating?.toFixed(0) ?? '—'} overall</div>
                </Link>
              </motion.div>
            ))}
          </div>
          <Link href="/fighters" className="inline-block mt-8 text-xs tracking-widest uppercase font-bold px-5 py-3 text-white" style={{ background: INK, ...hard('#ffffff', 5, 5) }}>Full roster →</Link>
        </div>
        <PopPortrait src="/fighters/f4.avif" th={th} scrollY={imgY} rotate={6} className="hidden lg:block w-[280px] xl:w-[360px] mt-10" />
      </div>
    </section>
  )
}

// ─── §6 MODEL (black, no image) ──────────────────────────────────────────────

const TRAINING_ACCURACY = 66.28
const AUC = 70.24
const LOG_LOSS = 0.639

function ModelBar({ label, value, max, unit, accent, isInView, delay }: { label: string; value: number; max: number; unit: string; accent: string; isInView: boolean; delay: number }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={isInView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.7, delay, ease: EXPO }} className="mb-6">
      <div className="flex justify-between mb-2">
        <span className="text-xs tracking-widest uppercase font-bold" style={{ color: 'rgba(10,10,12,0.66)' }}>{label}</span>
        <span className="text-sm font-bold tabular-nums" style={{ color: INK }}>{value}{unit}</span>
      </div>
      <div className="h-[10px] overflow-hidden" style={{ background: '#ffe0c2', border: `2px solid ${INK}` }}>
        <motion.div className="h-full" style={{ background: accent }} initial={{ width: 0 }} animate={isInView ? { width: `${pct}%` } : {}} transition={{ duration: 1.1, delay: delay + 0.1, ease: EXPO }} />
      </div>
    </motion.div>
  )
}

function ModelSection() {
  const th = T.model
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px 0px' })
  const xgb = summary.xgb_config as Record<string, unknown>
  const betsWon = Math.round(summary.bets_placed * summary.win_rate_when_bet)
  const betsLost = summary.bets_placed - betsWon

  return (
    <section id="model" ref={ref} className="relative px-6 py-28 overflow-hidden scroll-mt-14" style={{ background: th.bg, borderTop: `5px solid ${INK}` }}>
      <div className="halftone absolute inset-0 opacity-[0.09] pointer-events-none" style={{ color: INK }} />
      <div className="mx-auto max-w-7xl relative z-10">
        <div className="mb-16"><SectionHead label="Walk-forward XGBoost" title="THE MODEL" th={th} isInView={isInView} /></div>

        {/* Headline metrics — white pop-art cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-16">
          {[
            { label: 'ROI', value: summary.roi * 100, decimals: 1, suffix: '%', note: `${summary.start_date} → ${summary.end_date}`, color: th.accent2 },
            { label: 'Profit', value: summary.profit_units, decimals: 1, suffix: 'u', prefix: '+', note: `${summary.bets_placed} bets placed`, color: '#0fb890' },
            { label: 'Accuracy', value: TRAINING_ACCURACY, decimals: 2, suffix: '%', note: 'Train set · 15,206 fights', color: '#1a5fd4' },
            { label: 'Bets W/L', value: betsWon, decimals: 0, suffix: '', note: `${betsWon}W · ${betsLost}L`, color: INK },
          ].map(({ label, value, decimals, suffix, prefix, note, color }, i) => (
            <motion.div key={label} initial={{ opacity: 0, y: 50, scale: 0.85, rotate: i % 2 ? 3 : -3 }} animate={isInView ? { opacity: 1, y: 0, scale: 1, rotate: 0 } : {}} transition={{ ...SPRING, delay: 0.1 + i * 0.08 }}
              className="p-6 bg-white" style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}>
              <div className="font-bold leading-none tabular-nums mb-3" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(40px, 6vw, 72px)', color }}>
                {prefix}{value.toFixed(decimals)}{suffix}
              </div>
              <div className="text-[11px] tracking-widest uppercase font-bold" style={{ color: INK }}>{label}</div>
              <div className="text-[11px] mt-1" style={{ color: 'rgba(10,10,12,0.55)' }}>{note}</div>
            </motion.div>
          ))}
        </div>

        <motion.p initial={{ opacity: 0 }} animate={isInView ? { opacity: 1 } : {}} transition={{ duration: 0.6, delay: 0.4 }} className="text-base mb-16 max-w-2xl leading-relaxed font-medium" style={{ color: 'rgba(10,10,12,0.72)' }}>
          Backtest covers {summary.start_date}–{summary.end_date} using walk-forward retraining — the model is never evaluated on data it was trained on. Edge threshold: {(summary.edge_threshold * 100).toFixed(0)}% implied-probability gap.
        </motion.p>

        {/* Training metrics + dataset split — white cards */}
        <div className="grid md:grid-cols-2 gap-6 mb-16">
          <motion.div initial={{ opacity: 0, x: -30 }} animate={isInView ? { opacity: 1, x: 0 } : {}} transition={{ ...SPRING, delay: 0.2 }} className="p-8 bg-white" style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}>
            <p className="text-xs tracking-[0.3em] uppercase font-bold mb-8" style={{ color: th.accent2 }}>Training metrics</p>
            <ModelBar label="Training Accuracy" value={TRAINING_ACCURACY} max={100} unit="%" accent={th.accent2} isInView={isInView} delay={0.35} />
            <ModelBar label="AUC Score" value={AUC} max={100} unit="%" accent="#1a5fd4" isInView={isInView} delay={0.42} />
            <ModelBar label="Log Loss (lower = better)" value={Number(((1 - LOG_LOSS) * 100).toFixed(1))} max={100} unit="%" accent="#0fb890" isInView={isInView} delay={0.49} />
          </motion.div>
          <motion.div initial={{ opacity: 0, x: 30 }} animate={isInView ? { opacity: 1, x: 0 } : {}} transition={{ ...SPRING, delay: 0.28 }} className="p-8 bg-white" style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}>
            <p className="text-xs tracking-[0.3em] uppercase font-bold mb-6" style={{ color: th.accent2 }}>Dataset split</p>
            {[
              { k: 'Training rows', v: (15206).toLocaleString() },
              { k: 'Test rows', v: (1394).toLocaleString() },
              { k: 'Features used', v: '268' },
              { k: 'Best XGB iteration', v: '61' },
            ].map(({ k, v }) => (
              <div key={k} className="flex justify-between py-3" style={{ borderBottom: '2px solid #e7e2d6' }}>
                <span className="text-sm font-medium" style={{ color: 'rgba(10,10,12,0.6)' }}>{k}</span>
                <span className="text-lg font-bold tabular-nums" style={{ fontFamily: "'Space Grotesk', sans-serif", color: INK }}>{v}</span>
              </div>
            ))}
          </motion.div>
        </div>

        {/* XGBoost config — white cards */}
        {xgb && (
          <div>
            <p className="text-xs tracking-[0.3em] uppercase font-bold mb-6" style={{ color: INK }}>XGBoost config</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
              {Object.entries(xgb)
                .filter(([k]) => k !== 'eval_metric' && k !== 'n_jobs')
                .map(([k, v], i) => (
                  <motion.div key={k} initial={{ opacity: 0, y: 24 }} animate={isInView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.5, delay: 0.4 + i * 0.05, ease: EXPO }}
                    className="px-4 py-4 bg-white" style={{ border: `3px solid ${INK}`, ...hard(INK, 4, 4) }}>
                    <div className="text-2xl font-bold tabular-nums mb-1" style={{ fontFamily: "'Space Grotesk', sans-serif", color: INK }}>{String(v)}</div>
                    <div className="text-[10px] tracking-wide uppercase font-bold" style={{ color: 'rgba(10,10,12,0.5)' }}>{k.replace(/_/g, ' ')}</div>
                  </motion.div>
                ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

// ─── §1 HERO + main export ───────────────────────────────────────────────────

export default function HomeClient({ nextEvent, predictions, recentFights, topFighters }: HomeClientProps) {
  const th = T.hero
  const heroRef = useRef<HTMLDivElement>(null)
  const heroInView = useInView(heroRef, { once: true })
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ['start start', 'end start'] })
  const heroImgY = useTransform(scrollYProgress, [0, 1], ['0%', '-24%'])

  const stats = [
    { label: 'Total Bets', value: summary.bets_placed, decimals: 0, suffix: '', prefix: '', color: '#ff2e4d' },
    { label: 'ROI', value: summary.roi * 100, decimals: 1, suffix: '%', prefix: '', color: '#1a5fd4' },
    { label: 'Accuracy', value: 66.28, decimals: 1, suffix: '%', prefix: '', color: '#e08a00' },
  ]

  return (
    <div className="overflow-x-hidden" style={{ background: th.bg }}>
      {/* §1 HERO — cream comic splash */}
      <section id="top" ref={heroRef} className="relative min-h-screen flex flex-col justify-center px-6 overflow-hidden scroll-mt-14" style={{ background: th.bg }}>
        <div className="halftone-lg absolute inset-0 opacity-[0.06] pointer-events-none" style={{ color: '#ff2e4d' }} />
        <div className="absolute top-[12%] right-[10%] w-[280px] h-[280px] rounded-full blur-[120px] pointer-events-none" style={{ background: 'rgba(26,95,212,0.18)' }} />

        <div className="mx-auto max-w-7xl w-full relative z-10 grid lg:grid-cols-[1fr_auto] gap-12 items-center">
          <div>
            <motion.div initial={{ opacity: 0, x: -24 }} animate={heroInView ? { opacity: 1, x: 0 } : {}} transition={{ duration: 0.5, delay: 0.05, ease: 'easeOut' }}
              className="inline-flex items-center gap-3 mb-6 px-3 py-1" style={{ background: th.accent, ...hard(INK, 4, 4) }}>
              <p className="text-xs tracking-[0.3em] uppercase font-bold text-white">XGBoost · Walk-Forward · 2021–Now</p>
            </motion.div>

            <motion.h1 initial={{ opacity: 0, y: 80, skewY: 5 }} animate={heroInView ? { opacity: 1, y: 0, skewY: 0 } : {}} transition={{ duration: 1, delay: 0.1, ease: EXPO }}
              className="leading-[0.78] font-bold tracking-tighter uppercase mb-8" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(84px,16vw,210px)', color: th.text }}>
              UFC<br /><span style={{ color: th.accent, WebkitTextStroke: `3px ${INK}` }}>EDGE</span>
            </motion.h1>

            <motion.p initial={{ opacity: 0, y: 24 }} animate={heroInView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.7, delay: 0.18, ease: EXPO }} className="text-lg max-w-lg mb-12 leading-relaxed font-medium" style={{ color: th.sub }}>
Machine-learning model that finds positive-expected-value bets in UFC markets. Retrained on every historical card. No bias, no favourites.
            </motion.p>

            <div className="grid grid-cols-3 gap-4 mb-12 max-w-xl">
              {stats.map(({ label, value, decimals, suffix, prefix, color }, i) => (
                <motion.div key={label} initial={{ opacity: 0, y: 50, scale: 0.8, rotate: i % 2 ? 4 : -4 }} animate={heroInView ? { opacity: 1, y: 0, scale: 1, rotate: 0 } : {}} transition={{ ...SPRING, delay: 0.22 + i * 0.07 }}
                  className="p-4 bg-white" style={{ border: `3px solid ${INK}`, ...hard(INK, 5, 5) }}>
                  <div className="font-bold leading-none tabular-nums" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(30px,4.5vw,52px)', color }}>
                    <AnimatedCounter value={value} decimals={decimals} suffix={suffix} prefix={prefix} />
                  </div>
                  <div className="text-[10px] tracking-widest uppercase mt-2 font-bold" style={{ color: '#57534e' }}>{label}</div>
                </motion.div>
              ))}
            </div>

            <div className="flex flex-col md:flex-row gap-8 items-start">
              {nextEvent?.fight_date && (
                <motion.div initial={{ opacity: 0 }} animate={heroInView ? { opacity: 1 } : {}} transition={{ duration: 0.6, delay: 0.42 }}>
                  <Countdown target={nextEvent.fight_date} eventName={nextEvent.event_name} accent={th.accent} tone="light" />
                </motion.div>
              )}
              <motion.div initial={{ opacity: 0 }} animate={heroInView ? { opacity: 1 } : {}} transition={{ duration: 0.6, delay: 0.48 }} className="flex gap-4 flex-wrap items-center">
                <a href="#predictions" className="inline-flex items-center gap-2 text-xs font-bold tracking-widest uppercase px-6 py-3 text-white transition-transform hover:scale-105" style={{ background: th.accent, ...hard(INK, 5, 5) }}>Next Card ↓</a>
                <a href="#history" className="inline-flex items-center gap-2 text-xs font-bold tracking-widest uppercase px-6 py-3" style={{ background: '#fff', color: INK, border: `3px solid ${INK}`, ...hard(INK, 5, 5) }}>Fight History</a>
              </motion.div>
            </div>
          </div>

          {/* Hero portrait — f6 */}
          <motion.div style={{ y: heroImgY }} initial={{ opacity: 0, scale: 0.7, rotate: 8 }} animate={heroInView ? { opacity: 1, scale: 1, rotate: 3 } : {}} transition={{ ...SPRING, stiffness: 60, delay: 0.2 }} className="relative w-[300px] xl:w-[380px] hidden lg:block">
            <div className="halftone-lg absolute inset-0 -z-10 translate-x-5 translate-y-5" style={{ color: th.accent }} />
            <div className="absolute inset-0 -z-10 -translate-x-4 -translate-y-4" style={{ background: th.accent2 }} />
            <div className="relative aspect-[5/7] overflow-hidden" style={{ border: `4px solid ${INK}` }}>
              <Image src="/fighters/f6.avif" fill alt="" priority className="object-cover object-center" sizes="380px" />
            </div>
          </motion.div>
        </div>

        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2" style={{ color: '#78716c' }}>
          <motion.div animate={{ y: [0, 10, 0] }} transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}>
            <div className="w-[2px] h-16" style={{ background: `linear-gradient(to bottom, transparent, ${INK})` }} />
          </motion.div>
          <span className="text-[10px] tracking-[0.3em] uppercase font-bold">Scroll</span>
        </div>
      </section>

      <PredictionsSection predictions={predictions} />
      <FightHistorySection fights={recentFights} />
      <FightersSection fighters={topFighters} />
      <ModelSection />

      <footer className="px-6 py-8" style={{ background: INK, borderTop: `5px solid ${T.model.accent}` }}>
        <div className="mx-auto max-w-7xl flex items-center justify-between">
          <span className="text-xs text-[#a1a1aa]">UFC Edge — for informational purposes only</span>
          <span className="text-xs text-[#52525b]">{summary.start_date} – {summary.end_date}</span>
        </div>
      </footer>
    </div>
  )
}
