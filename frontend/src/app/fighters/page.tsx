import { createServerClient } from '@/lib/supabase'
import Link from 'next/link'
import { fmt, fmtPct } from '@/lib/utils'
import type { Fighter } from '@/lib/types'
import PopHeader from '@/components/PopHeader'
import Reveal from '@/components/Reveal'
import { INK, hard, PAGE_THEME } from '@/lib/pop'

const th = PAGE_THEME.fighters

export const revalidate = 3600

interface PageProps {
  searchParams: Promise<{ division?: string; sort?: string; q?: string }>
}

async function getFighters(params: Awaited<PageProps['searchParams']>): Promise<Fighter[]> {
  const db = createServerClient()
  const sort = params.sort ?? 'pre_fight_elo'
  const division = params.division ?? ''
  const q = params.q ?? ''

  let query = db.from('fighters').select('*')

  if (division) query = query.eq('division_norm', division)
  if (q) query = query.ilike('fighter_name', `%${q}%`)

  const { data } = await query
    .order(sort, { ascending: false, nullsFirst: false })
    .limit(100)

  return data ?? []
}

const GROTESK = "'Space Grotesk', sans-serif"

export default async function FightersPage({ searchParams }: PageProps) {
  const params = await searchParams
  const fighters = await getFighters(params)
  const sort = params.sort ?? 'pre_fight_elo'
  const division = params.division ?? ''

  const sortOptions = [
    { value: 'overall', label: 'Overall' },
    { value: 'pre_fight_elo', label: 'ELO' },
    { value: 'prior_wins', label: 'Wins' },
    { value: 'momentum', label: 'Momentum' },
  ]

  return (
    <div className="pt-14 min-h-screen" style={{ background: th.bg }}>
      <div className="mx-auto max-w-7xl px-6 py-16">
        <PopHeader label="Roster" title="Fighters" th={th} />

        <p className="mt-6 mb-10 text-sm font-bold uppercase tracking-widest" style={{ color: th.sub }}>
          Ranked by composite model rating. Click a fighter to view the full profile.
        </p>

        {/* FILTERS — GET form posting to URL */}
        <Reveal y={20}>
          <form className="flex flex-wrap gap-3 mb-8" method="GET">
            <input
              type="text"
              name="q"
              defaultValue={params.q ?? ''}
              placeholder="SEARCH FIGHTER..."
              className="bg-white text-xs font-bold uppercase tracking-widest px-4 py-2.5 w-52 focus:outline-none placeholder:text-[#a8a29e]"
              style={{ border: `2px solid ${INK}`, color: INK, fontFamily: GROTESK }}
            />
            <select
              name="sort"
              defaultValue={sort}
              className="bg-white text-xs font-bold uppercase tracking-widest px-3 py-2.5 focus:outline-none"
              style={{ border: `2px solid ${INK}`, color: INK, fontFamily: GROTESK }}
            >
              {sortOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <button
              type="submit"
              className="text-xs font-bold tracking-widest uppercase px-5 py-2.5 hover:-translate-y-0.5 transition-transform"
              style={{ background: th.accent, color: '#fff', border: `2px solid ${INK}`, ...hard(INK, 4, 4), fontFamily: GROTESK }}
            >
              Filter
            </button>
          </form>
        </Reveal>

        {/* COLUMN LABELS */}
        <div
          className="hidden md:flex items-center gap-4 px-4 mb-3 text-[10px] font-bold uppercase tracking-widest"
          style={{ color: th.sub, fontFamily: GROTESK }}
        >
          <span className="w-12 text-center">#</span>
          <span className="flex-1">Fighter</span>
          <span className="w-28 text-right">Record</span>
          <span className="w-20 text-right">Win Rate</span>
          <span className="w-16 text-right">ELO</span>
          <span className="w-20 text-right">Momentum</span>
          <span className="w-20 text-right">Overall</span>
        </div>

        {/* LEADERBOARD */}
        <Reveal y={30}>
          <div className="space-y-3">
            {fighters.map((f, i) => {
              const rank = i + 1
              return (
                <Link
                  key={f.fighter_id}
                  href={`/fighters/${encodeURIComponent(f.fighter_id)}`}
                  className="flex items-center gap-4 bg-white px-4 py-3 hover:-translate-y-0.5 transition-transform"
                  style={{ border: `3px solid ${INK}`, ...hard(INK, 5, 5) }}
                >
                  {/* RANK BLOCK */}
                  <span
                    className="w-12 shrink-0 text-center py-2 text-lg font-bold tabular-nums"
                    style={{
                      background: rank === 1 ? th.accent2 : INK,
                      color: '#fff',
                      fontFamily: GROTESK,
                    }}
                  >
                    {rank}
                  </span>

                  {/* NAME + DIVISION */}
                  <span className="flex-1 min-w-0">
                    <span
                      className="block truncate text-base font-bold uppercase tracking-tight"
                      style={{ color: INK, fontFamily: GROTESK }}
                    >
                      {f.fighter_name}
                    </span>
                    <span className="block text-[11px] font-bold uppercase tracking-widest" style={{ color: th.sub }}>
                      {f.division_norm ?? '—'}
                    </span>
                  </span>

                  {/* STATS */}
                  <span className="hidden md:block w-28 text-right tabular-nums text-sm font-bold" style={{ color: INK, fontFamily: GROTESK }}>
                    {f.prior_wins ?? 0}–{f.prior_losses ?? 0}–{f.prior_draws ?? 0}
                  </span>
                  <span className="hidden md:block w-20 text-right tabular-nums text-sm font-bold" style={{ color: INK, fontFamily: GROTESK }}>
                    {fmtPct(f.prior_win_rate)}
                  </span>
                  <span className="hidden md:block w-16 text-right tabular-nums text-sm" style={{ color: th.sub, fontFamily: GROTESK }}>
                    {fmt(f.pre_fight_elo, 0)}
                  </span>
                  <span className="hidden md:block w-20 text-right tabular-nums text-sm" style={{ color: th.sub, fontFamily: GROTESK }}>
                    {fmt(f.momentum)}
                  </span>

                  {/* OVERALL */}
                  <span
                    className="w-20 text-right tabular-nums text-2xl font-bold"
                    style={{ color: th.accent2, fontFamily: GROTESK }}
                  >
                    {fmt(f.overall)}
                  </span>
                </Link>
              )
            })}
          </div>
        </Reveal>

        <p className="text-xs font-bold uppercase tracking-widest mt-6" style={{ color: th.sub }}>
          Showing top {fighters.length} fighters
        </p>
      </div>
    </div>
  )
}
