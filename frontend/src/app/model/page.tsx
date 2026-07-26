import { createServerClient } from '@/lib/supabase'
import summary from '@/lib/summary.json'
import PopHeader from '@/components/PopHeader'
import Reveal from '@/components/Reveal'
import AnimatedCounter from '@/components/AnimatedCounter'
import ProfitChart, { type ProfitPoint } from '@/components/ProfitChart'
import { PAGE_THEME, POP, INK, hard } from '@/lib/pop'

export const revalidate = 3600

const th = PAGE_THEME.model // dark bg, orange accent

interface HistoryRow {
  fight_date: string
  predicted_correct: boolean | null
  profit_units: number | null
  bet_placed: boolean | null
  edge: number | null
}

async function getHistory(): Promise<HistoryRow[]> {
  const db = createServerClient()
  const { data } = await db
    .from('fight_history')
    .select('fight_date, predicted_correct, profit_units, bet_placed, edge')
    .order('fight_date', { ascending: true })
  return (data ?? []) as HistoryRow[]
}

interface TierRow { confidence_tier: string | null; prediction_correct: boolean | null }
async function getTierAccuracy() {
  const db = createServerClient()
  const { data } = await db
    .from('predictions')
    .select('confidence_tier, prediction_correct')
    .not('prediction_correct', 'is', null)
  const rows = (data ?? []) as TierRow[]
  const tiers = ['High', 'Medium', 'Low']
  return tiers.map((t) => {
    const subset = rows.filter((r) => r.confidence_tier === t)
    const correct = subset.filter((r) => r.prediction_correct === true).length
    return { tier: t, total: subset.length, correct, accuracy: subset.length ? (correct / subset.length) * 100 : 0 }
  })
}

// Build a cumulative-profit series (sampled so the chart stays readable).
function buildProfitSeries(bets: HistoryRow[]): ProfitPoint[] {
  let run = 0
  const full = bets.map((b) => {
    run += b.profit_units ?? 0
    return { date: b.fight_date, cumulative: run }
  })
  if (full.length <= 120) return full
  const step = Math.ceil(full.length / 120)
  const sampled = full.filter((_, i) => i % step === 0)
  if (sampled[sampled.length - 1] !== full[full.length - 1]) sampled.push(full[full.length - 1])
  return sampled
}

const TIER_COLOR: Record<string, string> = { High: POP.red, Medium: POP.orange, Low: '#71717a' }

export default async function ModelPage() {
  const [history, tierAcc] = await Promise.all([getHistory(), getTierAccuracy()])
  const bets = history.filter((h) => h.bet_placed)
  const wins = bets.filter((h) => h.predicted_correct === true).length
  const losses = bets.filter((h) => h.predicted_correct === false).length
  const series = buildProfitSeries(bets)

  return (
    <div className="pt-14 min-h-screen" style={{ background: th.bg }}>
      <div className="mx-auto max-w-6xl px-6 py-16">
        <PopHeader label="Backtest" title="Model Performance" th={th} />

        {/* HERO STATS */}
        <Reveal y={20}>
          <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div
              className="px-4 py-6 text-center"
              style={{ background: '#1a1a1f', border: `3px solid ${POP.orange}`, ...hard(POP.orange, 4, 4) }}
            >
              <div className="text-2xl font-black tabular-nums" style={{ color: POP.orange }}>
                <AnimatedCounter value={summary.roi * 100} decimals={1} suffix="%" />
              </div>
              <div className="mt-1 text-xs font-bold uppercase tracking-widest" style={{ color: th.sub }}>
                ROI
              </div>
            </div>
            <div
              className="px-4 py-6 text-center"
              style={{ background: '#1a1a1f', border: `3px solid ${POP.yellow}`, ...hard(POP.yellow, 4, 4) }}
            >
              <div className="text-2xl font-black tabular-nums" style={{ color: POP.yellow }}>
                <AnimatedCounter value={summary.bets_placed} />
              </div>
              <div className="mt-1 text-xs font-bold uppercase tracking-widest" style={{ color: th.sub }}>
                Bets Placed
              </div>
            </div>
            <div
              className="px-4 py-6 text-center"
              style={{ background: '#1a1a1f', border: `3px solid ${POP.teal}`, ...hard(POP.teal, 4, 4) }}
            >
              <div className="text-2xl font-black tabular-nums" style={{ color: POP.teal }}>
                {wins}-{losses}
              </div>
              <div className="mt-1 text-xs font-bold uppercase tracking-widest" style={{ color: th.sub }}>
                Record
              </div>
            </div>
            <div
              className="px-4 py-6 text-center"
              style={{ background: '#1a1a1f', border: `3px solid ${POP.red}`, ...hard(POP.red, 4, 4) }}
            >
              <div className="text-2xl font-black tabular-nums" style={{ color: POP.red }}>
                <AnimatedCounter value={summary.profit_units} decimals={1} suffix="u" />
              </div>
              <div className="mt-1 text-xs font-bold uppercase tracking-widest" style={{ color: th.sub }}>
                Profit (units)
              </div>
            </div>
          </div>
        </Reveal>

        {/* CUMULATIVE PROFIT CHART */}
        <Reveal y={20} delay={0.1}>
          <div className="mt-14">
            <h2 className="text-sm font-black uppercase tracking-widest mb-5" style={{ color: th.sub }}>
              Cumulative Profit (units staked)
            </h2>
            <div className="p-4" style={{ background: '#1a1a1f', border: `3px solid ${INK}` }}>
              <ProfitChart data={series} />
            </div>
          </div>
        </Reveal>

        {/* ACCURACY BY CONFIDENCE TIER */}
        <Reveal y={20} delay={0.15}>
          <div className="mt-14">
            <h2 className="text-sm font-black uppercase tracking-widest mb-5" style={{ color: th.sub }}>
              Accuracy by Confidence Tier
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              {tierAcc.map((t) => (
                <div
                  key={t.tier}
                  className="p-5"
                  style={{ background: '#1a1a1f', border: `3px solid ${TIER_COLOR[t.tier]}` }}
                >
                  <div className="flex items-baseline justify-between mb-3">
                    <span className="text-xs font-bold uppercase tracking-widest" style={{ color: th.sub }}>
                      {t.tier} confidence
                    </span>
                    <span className="text-xs" style={{ color: th.sub }}>{t.total} picks</span>
                  </div>
                  <div className="text-3xl font-black tabular-nums" style={{ color: TIER_COLOR[t.tier] }}>
                    {t.accuracy.toFixed(1)}%
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden" style={{ background: '#0a0a0c' }}>
                    <div className="h-full" style={{ width: `${t.accuracy}%`, background: TIER_COLOR[t.tier] }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Reveal>

        {/* TRAINING NOTES */}
        <Reveal y={20} delay={0.2}>
          <div className="mt-14 p-6" style={{ background: '#1a1a1f', border: `2px solid ${th.sub}` }}>
            <p className="text-xs uppercase tracking-widest font-bold mb-2" style={{ color: th.sub }}>
              Backtest window
            </p>
            <p className="text-sm" style={{ color: '#e4e4e7' }}>
              {summary.start_date} → {summary.end_date} · {summary.historical_fights_in_window} fights in window ·{' '}
              {summary.matched_fights} matched · {summary.model_retrain_dates} retrain checkpoints
            </p>
            <p className="mt-3 text-xs" style={{ color: th.sub }}>{summary.note}</p>
          </div>
        </Reveal>
      </div>
    </div>
  )
}
