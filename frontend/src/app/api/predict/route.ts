import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@/lib/supabase'

// Server-only route. The Supabase client here runs on the server with the
// read-only anon key; no key is ever exposed to the browser. If a service-role
// key is ever needed, it must be read from a server env var HERE and nowhere else.
export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const COLS =
  'fighter_id, fighter_name, division_norm, overall, pre_fight_elo, prior_wins, prior_losses, prior_win_rate, striking_offense, striking_defense, grappling_offense, grappling_defense, finishing_durability, momentum, physical, experience_big_fight'

interface FighterRow {
  fighter_id: string
  fighter_name: string
  division_norm: string | null
  overall: number | null
  pre_fight_elo: number | null
  prior_wins: number | null
  prior_losses: number | null
  prior_win_rate: number | null
  striking_offense: number | null
  striking_defense: number | null
  grappling_offense: number | null
  grappling_defense: number | null
  finishing_durability: number | null
  momentum: number | null
  physical: number | null
  experience_big_fight: number | null
}

type DB = ReturnType<typeof createServerClient>

async function fetchFighter(db: DB, key: string): Promise<FighterRow | null> {
  const byId = await db.from('fighters').select(COLS).eq('fighter_id', key).limit(1).maybeSingle()
  if (byId.data) return byId.data as FighterRow
  const byName = await db.from('fighters').select(COLS).ilike('fighter_name', key).limit(1).maybeSingle()
  return (byName.data as FighterRow) ?? null
}

const n = (v: number | null | undefined, d = 50) => (v == null || Number.isNaN(v) ? d : v)
const logistic = (x: number) => 1 / (1 + Math.exp(-x))
const clamp = (x: number, lo = 0.03, hi = 0.97) => Math.max(lo, Math.min(hi, x))

function predict(a: FighterRow, b: FighterRow) {
  // 1) ELO expectation
  const pElo = 1 / (1 + Math.pow(10, (n(b.pre_fight_elo, 1500) - n(a.pre_fight_elo, 1500)) / 400))
  // 2) Overall rating gap
  const pOverall = logistic((n(a.overall) - n(b.overall)) / 8)
  // 3) Style matchup: my offense vs your defense
  const striking = n(a.striking_offense) - n(b.striking_defense) - (n(b.striking_offense) - n(a.striking_defense))
  const grappling = n(a.grappling_offense) - n(b.grappling_defense) - (n(b.grappling_offense) - n(a.grappling_defense))
  const pStyle = logistic((striking + grappling) / 40)
  // 4) Momentum + big-fight experience
  const pForm = logistic((n(a.momentum) - n(b.momentum)) / 25 + (n(a.experience_big_fight) - n(b.experience_big_fight)) / 60)

  const probA = clamp(0.45 * pElo + 0.28 * pOverall + 0.17 * pStyle + 0.1 * pForm)
  const probB = 1 - probA
  const margin = Math.abs(probA - probB)
  const tier = margin >= 0.28 ? 'High' : margin >= 0.14 ? 'Medium' : 'Low'
  const winner = probA >= probB ? a : b

  return {
    probA,
    probB,
    tier,
    predicted_winner: winner.fighter_name,
    factors: [
      { key: 'ELO', a: Math.round(n(a.pre_fight_elo, 1500)), b: Math.round(n(b.pre_fight_elo, 1500)), edge: pElo },
      { key: 'Overall', a: Math.round(n(a.overall)), b: Math.round(n(b.overall)), edge: pOverall },
      { key: 'Style', a: Math.round(n(a.striking_offense)), b: Math.round(n(b.striking_offense)), edge: pStyle },
      { key: 'Form', a: Math.round(n(a.momentum)), b: Math.round(n(b.momentum)), edge: pForm },
    ],
  }
}

async function handle(aKey: string | null, bKey: string | null) {
  if (!aKey || !bKey) {
    return NextResponse.json({ error: 'Provide both fighter ids/names via `a` and `b`.' }, { status: 400 })
  }
  if (aKey === bKey) {
    return NextResponse.json({ error: 'Pick two different fighters.' }, { status: 400 })
  }
  const db = createServerClient()
  const [a, b] = await Promise.all([fetchFighter(db, aKey), fetchFighter(db, bKey)])
  if (!a) return NextResponse.json({ error: `Fighter not found: ${aKey}` }, { status: 404 })
  if (!b) return NextResponse.json({ error: `Fighter not found: ${bKey}` }, { status: 404 })

  const result = predict(a, b)
  return NextResponse.json({
    model: 'ratings-heuristic-v1',
    note: 'On-demand estimate from current fighter ratings/ELO — not the walk-forward XGBoost backtest.',
    a: { id: a.fighter_id, name: a.fighter_name, division: a.division_norm, record: `${a.prior_wins ?? 0}-${a.prior_losses ?? 0}` },
    b: { id: b.fighter_id, name: b.fighter_name, division: b.division_norm, record: `${b.prior_wins ?? 0}-${b.prior_losses ?? 0}` },
    ...result,
  })
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  return handle(searchParams.get('a'), searchParams.get('b'))
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  return handle(body?.a ?? null, body?.b ?? null)
}
