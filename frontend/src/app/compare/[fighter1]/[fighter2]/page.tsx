import { createServerClient } from '@/lib/supabase'
import { deslugify, fmt, fmtPct } from '@/lib/utils'
import Link from 'next/link'
import type { Fighter } from '@/lib/types'
import CompareBar from '@/components/CompareBar'
import { INK, hard, PAGE_THEME } from '@/lib/pop'
import PopHeader from '@/components/PopHeader'
import Reveal from '@/components/Reveal'

const th = PAGE_THEME.compare

interface PageProps {
  params: Promise<{ fighter1: string; fighter2: string }>
}

async function getFighter(name: string): Promise<Fighter | null> {
  const db = createServerClient()
  const decoded = deslugify(name)
  const { data } = await db
    .from('fighters')
    .select('*')
    .ilike('fighter_name', decoded)
    .limit(1)
    .single()
  return data ?? null
}

const ratingKeys: { key: keyof Fighter; label: string }[] = [
  { key: 'overall', label: 'Overall Rating' },
  { key: 'pre_fight_elo', label: 'ELO Rating' },
  { key: 'striking_offense', label: 'Striking Offense' },
  { key: 'striking_defense', label: 'Striking Defense' },
  { key: 'grappling_offense', label: 'Grappling Offense' },
  { key: 'grappling_defense', label: 'Grappling Defense' },
  { key: 'finishing_durability', label: 'Finishing / Durability' },
  { key: 'momentum', label: 'Momentum' },
  { key: 'physical', label: 'Physical' },
  { key: 'experience_big_fight', label: 'Big Fight Exp.' },
]

const avgKeys: { key: keyof Fighter; label: string }[] = [
  { key: 'avg_sig_landed_for', label: 'Sig. Strikes Landed / min' },
  { key: 'avg_sig_landed_against', label: 'Sig. Strikes Absorbed / min' },
  { key: 'avg_td_landed_for', label: 'Takedowns Landed / 15min' },
  { key: 'avg_td_landed_against', label: 'Takedowns Absorbed / 15min' },
  { key: 'avg_kd_for', label: 'Knockdowns / fight' },
  { key: 'avg_ctrl_seconds_for', label: 'Control Time (s) / fight' },
  { key: 'avg_sub_att_for', label: 'Sub Attempts / fight' },
]

export default async function ComparePage({ params }: PageProps) {
  const { fighter1, fighter2 } = await params
  const [a, b] = await Promise.all([getFighter(fighter1), getFighter(fighter2)])

  if (!a || !b) {
    return (
      <div className="pt-14 min-h-screen flex items-center justify-center" style={{ background: th.bg }}>
        <div
          className="text-center px-10 py-12"
          style={{ background: '#ffffff', border: '3px solid ' + INK, ...hard(INK, 6, 6) }}
        >
          <p className="text-sm tracking-widest uppercase font-bold mb-4" style={{ color: INK }}>
            Fighter not found
          </p>
          <Link
            href="/fights"
            className="text-xs tracking-widest uppercase font-bold"
            style={{ color: th.accent }}
          >
            ← Back to fights
          </Link>
        </div>
      </div>
    )
  }

  const winner = (a.overall ?? 0) >= (b.overall ?? 0) ? a : b

  return (
    <div className="pt-14 min-h-screen" style={{ background: th.bg }}>
      <div className="mx-auto max-w-4xl px-6 py-16">
        <PopHeader label="Head to Head" title={`${a.fighter_name} vs ${b.fighter_name}`} th={th} />

        <Reveal y={20}>
          <div className="mt-6 mb-10 text-sm font-bold uppercase tracking-widest" style={{ color: th.sub }}>
            Model favors{' '}
            <span style={{ color: th.accent }}>{winner.fighter_name}</span>
            {a.division_norm && ` · ${a.division_norm}`}
          </div>
        </Reveal>

        <Reveal y={20} delay={0.05}>
          <div className="grid grid-cols-2 gap-6 mb-14">
            {[a, b].map((f) => (
              <div
                key={f.fighter_id}
                className="p-6"
                style={{ background: '#ffffff', border: '3px solid ' + INK, ...hard(INK, 5, 5) }}
              >
                <div className="text-lg font-black" style={{ color: INK }}>{f.fighter_name}</div>
                <div className="mt-1 text-xs font-bold uppercase tracking-widest" style={{ color: th.sub }}>
                  {(f.prior_wins ?? 0)}-{(f.prior_losses ?? 0)} · {fmtPct(f.prior_win_rate)} win rate
                </div>
                <div className="mt-3 text-2xl font-black tabular-nums" style={{ color: th.accent }}>
                  {fmt(f.overall)}
                </div>
                <div className="text-[10px] font-bold uppercase tracking-widest" style={{ color: th.sub }}>
                  Overall Rating
                </div>
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal y={20} delay={0.1}>
          <div className="mb-14">
            <h2 className="text-sm font-black uppercase tracking-widest mb-6" style={{ color: th.sub }}>
              Model Ratings
            </h2>
            <div className="flex flex-col gap-5">
              {ratingKeys.map(({ key, label }) => {
                const aVal = typeof a[key] === 'number' ? (a[key] as number) : 0
                const bVal = typeof b[key] === 'number' ? (b[key] as number) : 0
                return (
                  <CompareBar
                    key={String(key)}
                    label={label}
                    aValue={aVal}
                    bValue={bVal}
                    aName={a.fighter_name}
                    bName={b.fighter_name}
                  />
                )
              })}
            </div>
          </div>
        </Reveal>

        <Reveal y={20} delay={0.15}>
          <div>
            <h2 className="text-sm font-black uppercase tracking-widest mb-6" style={{ color: th.sub }}>
              Career Averages
            </h2>
            <div className="grid grid-cols-1 gap-5">
              {avgKeys.map(({ key, label }) => {
                const aVal = typeof a[key] === 'number' ? (a[key] as number) : 0
                const bVal = typeof b[key] === 'number' ? (b[key] as number) : 0
                return (
                  <CompareBar
                    key={String(key)}
                    label={label}
                    aValue={aVal}
                    bValue={bVal}
                    aName={a.fighter_name}
                    bName={b.fighter_name}
                  />
                )
              })}
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  )
}
