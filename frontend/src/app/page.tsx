import { createServerClient } from '@/lib/supabase'
import HomeClient from '@/components/HomeClient'
import type { RecentPrediction, RecentFight, TopFighter } from '@/components/HomeClient'

export const revalidate = 3600

async function getNextEvent() {
  const db = createServerClient()
  const today = new Date().toISOString().split('T')[0]
  const { data } = await db
    .from('predictions')
    .select('event_name, fight_date')
    .gte('fight_date', today)
    .order('fight_date', { ascending: true })
    .limit(1)
    .single()
  return data ?? null
}

async function getPredictions(): Promise<RecentPrediction[]> {
  const db = createServerClient()
  const today = new Date().toISOString().split('T')[0]
  // Try upcoming first
  const { data: upcoming } = await db
    .from('predictions')
    .select('fight_id_manual, event_name, fight_date, fighter_a, fighter_b, predicted_winner, a_win_probability, b_win_probability, confidence_tier, division_norm')
    .gte('fight_date', today)
    .order('fight_date', { ascending: true })
    .limit(9)
  if (upcoming && upcoming.length > 0) return upcoming as RecentPrediction[]
  // Fall back to most recent past predictions
  const { data: past } = await db
    .from('predictions')
    .select('fight_id_manual, event_name, fight_date, fighter_a, fighter_b, predicted_winner, a_win_probability, b_win_probability, confidence_tier, division_norm')
    .order('fight_date', { ascending: false })
    .limit(9)
  return (past ?? []) as RecentPrediction[]
}

async function getRecentFights(): Promise<RecentFight[]> {
  const db = createServerClient()
  // fight_history's real columns are a_fighter_name / b_fighter_name / actual_winner / division_norm
  // (no fighter_a/winner/division/method columns exist on this table) — aliased to what HomeClient expects.
  const { data } = await db
    .from('fight_history')
    .select(
      'fight_id, event_name, fight_date, fighter_a:a_fighter_name, fighter_b:b_fighter_name, winner:actual_winner, division:division_norm'
    )
    .order('fight_date', { ascending: false })
    .limit(10)
  return ((data ?? []) as unknown as RecentFight[]).map((f) => ({
    ...f,
    method: null, // fight_history has no method column; nothing to map here
  }))
}

async function getTopFighters(): Promise<TopFighter[]> {
  const db = createServerClient()
  // Alias the real schema columns (see src/lib/types.ts) to the names HomeClient expects.
  const { data } = await db
    .from('fighters')
    .select('fighter_id, fighter_name, overall_rating:overall, elo_rating:pre_fight_elo, wins:prior_wins, losses:prior_losses, win_rate:prior_win_rate, division:division_norm, striking_offense, grappling_offense, conditioning_score:physical, takedown_offense:grappling_defense, momentum_score:momentum')
    .order('overall', { ascending: false })
    .limit(10)
  return (data ?? []) as unknown as TopFighter[]
}

export default async function HomePage() {
  const [nextEvent, predictions, recentFights, topFighters] = await Promise.all([
    getNextEvent(),
    getPredictions(),
    getRecentFights(),
    getTopFighters(),
  ])

  return (
    <div className="pt-14">
      <HomeClient
        nextEvent={nextEvent}
        predictions={predictions}
        recentFights={recentFights}
        topFighters={topFighters}
      />
    </div>
  )
}
