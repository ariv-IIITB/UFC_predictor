import { createServerClient } from '@/lib/supabase'
import { fmt, fmtPct, fmtDate } from '@/lib/utils'
import Link from 'next/link'
import type { Fighter } from '@/lib/types'
import { INK, POP, hard, PAGE_THEME } from '@/lib/pop'
import PopHeader from '@/components/PopHeader'
import Reveal from '@/components/Reveal'

interface PageProps {
  params: Promise<{ fighter_id: string }>
}

async function getFighter(id: string): Promise<Fighter | null> {
  const db = createServerClient()
  const decoded = decodeURIComponent(id)

  // Try by ID first, then by name
  const { data: byId } = await db.from('fighters').select('*').eq('fighter_id', decoded).limit(1).single()
  if (byId) return byId

  const { data: byName } = await db.from('fighters').select('*').ilike('fighter_name', decoded).limit(1).single()
  return byName ?? null
}

const ratingKeys: { key: keyof Fighter; label: string; max?: number }[] = [
  { key: 'overall',              label: 'Overall',              max: 100 },
  { key: 'pre_fight_elo',        label: 'ELO',                  max: 2000 },
  { key: 'striking_offense',     label: 'Striking Offense',     max: 100 },
  { key: 'striking_defense',     label: 'Striking Defense',     max: 100 },
  { key: 'grappling_offense',    label: 'Grappling Offense',    max: 100 },
  { key: 'grappling_defense',    label: 'Grappling Defense',    max: 100 },
  { key: 'finishing_durability', label: 'Finishing/Durability', max: 100 },
  { key: 'momentum',             label: 'Momentum',             max: 100 },
  { key: 'physical',             label: 'Physical',             max: 100 },
]

const th = PAGE_THEME.fighter
const GROTESK = "'Space Grotesk', sans-serif"

export default async function FighterPage({ params }: PageProps) {
  const { fighter_id } = await params
  const fighter = await getFighter(fighter_id)

  if (!fighter) {
    return (
      <div className="pt-14 min-h-screen flex items-center justify-center" style={{ background: th.bg }}>
        <div
          className="text-center bg-white px-10 py-10"
          style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}
        >
          <p
            className="text-sm tracking-widest uppercase font-bold mb-5"
            style={{ color: INK, fontFamily: GROTESK }}
          >
            Fighter not found
          </p>
          <Link
            href="/fighters"
            className="inline-block text-[11px] tracking-widest uppercase font-bold px-3 py-1.5"
            style={{ background: th.accent, color: '#fff', border: `2px solid ${INK}`, ...hard(INK, 3, 3) }}
          >
            ← All Fighters
          </Link>
        </div>
      </div>
    )
  }

  const finishRate = fighter.prior_wins
    ? ((fighter.prior_finish_wins ?? 0) / fighter.prior_wins) * 100
    : 0

  const bio = [
    { label: 'Record', value: `${fighter.prior_wins ?? 0}–${fighter.prior_losses ?? 0}–${fighter.prior_draws ?? 0}` },
    { label: 'Height', value: fighter.height ? `${fighter.height}"` : '—' },
    { label: 'Reach', value: fighter.reach ? `${fighter.reach}"` : '—' },
    { label: 'Stance', value: fighter.stance ?? '—' },
    { label: 'Age', value: fighter.age_years ? `${Math.floor(fighter.age_years)}` : '—' },
    { label: 'Last fight', value: fmtDate(fighter.last_fight_date) },
  ]

  const overallStats = [
    { label: 'Overall', value: fmt(fighter.overall), accent: true },
    { label: 'ELO', value: fmt(fighter.pre_fight_elo, 0) },
    { label: 'Win Rate', value: fmtPct(fighter.prior_win_rate) },
    { label: 'Finish Rate', value: `${finishRate.toFixed(0)}%` },
  ]

  const careerStats = [
    { label: 'Sig. Strikes / min', value: fmt(fighter.avg_sig_landed_for, 2) },
    { label: 'Absorbed / min', value: fmt(fighter.avg_sig_landed_against, 2) },
    { label: 'Takedowns / 15min', value: fmt(fighter.avg_td_landed_for, 2) },
    { label: 'TD Absorbed', value: fmt(fighter.avg_td_landed_against, 2) },
    { label: 'Knockdowns / fight', value: fmt(fighter.avg_kd_for, 2) },
    { label: 'Ctrl time (s)', value: fmt(fighter.avg_ctrl_seconds_for, 0) },
    { label: 'Sub attempts', value: fmt(fighter.avg_sub_att_for, 2) },
    { label: 'Finish wins', value: fighter.prior_finish_wins ?? '—' },
    { label: 'Title fights', value: fighter.prior_title_fights ?? '—' },
  ]

  const record = [
    { label: 'Wins', value: fighter.prior_wins ?? 0, color: POP.teal },
    { label: 'Losses', value: fighter.prior_losses ?? 0, color: POP.redDeep },
    { label: 'Draws / NC', value: (fighter.prior_draws ?? 0) + (fighter.prior_no_contests ?? 0), color: INK },
    { label: 'Decision Wins', value: fighter.prior_decision_wins ?? 0, color: POP.blue },
  ]

  return (
    <div className="pt-14 min-h-screen" style={{ background: th.bg }}>
      <div className="mx-auto max-w-6xl px-6 py-16">
        {/* BACK */}
        <div className="mb-8">
          <Link
            href="/fighters"
            className="inline-block text-[11px] tracking-widest uppercase font-bold px-3 py-1.5"
            style={{ background: th.accent, color: '#fff', border: `2px solid ${INK}`, ...hard(INK, 3, 3) }}
          >
            ← All Fighters
          </Link>
        </div>

        {/* NAME + BIO */}
        <PopHeader
          label={fighter.division_norm ?? 'Fighter'}
          title={fighter.fighter_name}
          th={th}
        />

        <Reveal delay={0.05} y={24} className="mt-8 mb-12">
          <div
            className="bg-white p-6 flex flex-wrap gap-x-10 gap-y-5"
            style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}
          >
            {bio.map(({ label, value }) => (
              <div key={label}>
                <div className="text-[10px] tracking-widest uppercase font-bold mb-1" style={{ color: th.sub }}>
                  {label}
                </div>
                <div className="text-lg font-bold" style={{ color: INK, fontFamily: GROTESK }}>
                  {value}
                </div>
              </div>
            ))}
          </div>
        </Reveal>

        {/* OVERALL RATING */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-14">
          {overallStats.map(({ label, value, accent }, i) => (
            <Reveal key={label} delay={i * 0.06} y={30}>
              <div
                className="bg-white p-6 h-full"
                style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}
              >
                <div
                  className="text-5xl font-bold mb-2 tabular-nums leading-none"
                  style={{ fontFamily: GROTESK, color: accent ? th.accent : INK }}
                >
                  {value}
                </div>
                <div className="text-[10px] tracking-widest uppercase font-bold" style={{ color: th.sub }}>
                  {label}
                </div>
              </div>
            </Reveal>
          ))}
        </div>

        {/* RATINGS BARS */}
        <Reveal y={30} className="mb-14">
          <div className="bg-white p-8" style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}>
            <p className="text-xs tracking-[0.25em] uppercase font-bold mb-7" style={{ color: INK }}>
              Composite ratings
            </p>
            <div className="space-y-6">
              {ratingKeys.map(({ key, label, max = 100 }) => {
                const val = (fighter[key] as number | null) ?? 0
                const pct = Math.min((val / max) * 100, 100)
                return (
                  <div key={key}>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="font-bold" style={{ color: th.sub }}>{label}</span>
                      <span className="tabular-nums font-bold" style={{ color: INK, fontFamily: GROTESK }}>
                        {val.toFixed(1)}
                      </span>
                    </div>
                    <div
                      className="h-4 w-full overflow-hidden"
                      style={{ background: '#e7e2d6', border: `1.5px solid ${INK}` }}
                    >
                      <div
                        className="h-full transition-all duration-1000"
                        style={{ width: `${pct}%`, background: th.accent }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </Reveal>

        {/* FIGHT STATS */}
        <div className="mb-14">
          <p className="text-xs tracking-[0.25em] uppercase font-bold mb-6" style={{ color: INK }}>
            Career averages
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
            {careerStats.map(({ label, value }, i) => (
              <Reveal key={label} delay={(i % 3) * 0.05} y={26}>
                <div
                  className="bg-white p-5 h-full"
                  style={{ border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}
                >
                  <div
                    className="text-3xl font-bold mb-1 tabular-nums leading-none"
                    style={{ fontFamily: GROTESK, color: INK }}
                  >
                    {value}
                  </div>
                  <div className="text-[10px] tracking-widest uppercase font-bold" style={{ color: th.sub }}>
                    {label}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>

        {/* RECORD BREAKDOWN */}
        <div>
          <p className="text-xs tracking-[0.25em] uppercase font-bold mb-6" style={{ color: INK }}>
            Record breakdown
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            {record.map(({ label, value, color }, i) => (
              <Reveal key={label} delay={i * 0.06} y={30}>
                <div
                  className="p-6 h-full"
                  style={{ background: color, border: `3px solid ${INK}`, ...hard(INK, 6, 6) }}
                >
                  <div
                    className="text-4xl font-bold mb-1 tabular-nums leading-none"
                    style={{ fontFamily: GROTESK, color: '#fff' }}
                  >
                    {value}
                  </div>
                  <div className="text-[10px] tracking-widest uppercase font-bold" style={{ color: '#fff', opacity: 0.85 }}>
                    {label}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
