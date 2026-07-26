import { createServerClient } from '@/lib/supabase'
import Link from 'next/link'
import { fmtDate } from '@/lib/utils'
import type { Prediction } from '@/lib/types'
import { INK, POP, hard, PAGE_THEME, TIER_COLOR } from '@/lib/pop'
import PopHeader from '@/components/PopHeader'
import Reveal from '@/components/Reveal'

export const revalidate = 900

const th = PAGE_THEME.predict

async function getPredictions(): Promise<Prediction[]> {
  const db = createServerClient()
  const { data } = await db
    .from('predictions')
    .select('*')
    .order('fight_date', { ascending: true })
    .order('confidence_tier', { ascending: true })
  return data ?? []
}

function groupByEvent(predictions: Prediction[]): Record<string, Prediction[]> {
  return predictions.reduce<Record<string, Prediction[]>>((acc, p) => {
    const key = `${p.event_name ?? 'Unknown'} — ${fmtDate(p.fight_date)}`
    if (!acc[key]) acc[key] = []
    acc[key].push(p)
    return acc
  }, {})
}

export default async function PredictPage() {
  const predictions = await getPredictions()
  const grouped = groupByEvent(predictions)

  return (
    <div className="pt-14 min-h-screen" style={{ background: th.bg }}>
      <div className="mx-auto max-w-5xl px-6 py-16">
        <div className="mb-12">
          <PopHeader label="Next Card" title="Predictions" th={th} />
          <p className="text-sm mt-6 max-w-2xl" style={{ color: th.sub }}>
            Model picks for upcoming events. Confidence tier reflects edge strength and probability margin.
          </p>
        </div>

        {Object.keys(grouped).length === 0 && (
          <div
            className="p-16 text-center"
            style={{ background: '#ffffff', border: '3px solid ' + INK, ...hard(INK, 6, 6) }}
          >
            <p className="text-sm tracking-widest uppercase font-bold" style={{ color: INK }}>
              No upcoming predictions yet
            </p>
          </div>
        )}

        <div className="space-y-16">
          {Object.entries(grouped).map(([eventKey, fights], gi) => (
            <Reveal key={eventKey} delay={gi * 0.05}>
              <div>
                <div className="flex items-end gap-6 mb-6">
                  <div>
                    <h2
                      className="text-2xl md:text-3xl font-bold uppercase tracking-tight"
                      style={{ fontFamily: "'Space Grotesk', sans-serif", color: INK }}
                    >
                      {eventKey}
                    </h2>
                    <div className="mt-2 h-1.5 w-24" style={{ background: th.accent }} />
                  </div>
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 uppercase tracking-widest text-white"
                    style={{ background: INK }}
                  >
                    {fights.length} fights
                  </span>
                </div>

                <div className="space-y-4">
                  {fights.map((p, fi) => {
                    const tierKey = p.confidence_tier ?? ''
                    const tierColor = TIER_COLOR[tierKey] ?? '#71717a'
                    const aProb = p.a_win_probability ?? 0
                    const bProb = p.b_win_probability ?? 0
                    const aWins = p.predicted_winner === p.fighter_a
                    const winnerProb = aWins ? aProb : bProb
                    const loserProb = aWins ? bProb : aProb

                    return (
                      <Reveal key={p.fight_id_manual} delay={fi * 0.04}>
                        <div
                          className="group hover:-translate-y-0.5 transition-transform"
                          style={{ background: '#ffffff', border: '3px solid ' + INK, ...hard(INK, 6, 6) }}
                        >
                          <div className="p-5">
                            <div className="flex items-start justify-between gap-4 mb-4">
                              <span className="text-[10px] tracking-widest uppercase font-bold" style={{ color: th.sub }}>
                                {p.division_norm}
                              </span>
                              <div className="flex items-center gap-2 shrink-0">
                                {p.confidence_tier && (
                                  <span
                                    className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-white"
                                    style={{ background: tierColor }}
                                  >
                                    {p.confidence_tier} confidence
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* MATCHUP */}
                            <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center mb-5">
                              <div className={aWins ? '' : 'opacity-50'}>
                                <Link
                                  href={`/fighters/${encodeURIComponent(p.fighter_a)}`}
                                  className="block text-sm font-bold mb-1 transition-colors hover:text-[var(--acc)]"
                                  style={{ fontFamily: "'Space Grotesk', sans-serif", color: INK, ['--acc' as string]: th.accent2 }}
                                >
                                  {p.fighter_a}
                                </Link>
                                <div
                                  className="text-2xl font-bold tabular-nums"
                                  style={{ color: aWins ? tierColor : '#a8a29e', fontFamily: "'Space Grotesk', sans-serif" }}
                                >
                                  {(aProb * 100).toFixed(0)}%
                                </div>
                              </div>

                              <div className="text-center">
                                <div className="text-xs font-bold" style={{ color: INK }}>vs</div>
                              </div>

                              <div className={cn('text-right', !aWins ? '' : 'opacity-50')}>
                                <Link
                                  href={`/fighters/${encodeURIComponent(p.fighter_b)}`}
                                  className="block text-sm font-bold mb-1 transition-colors hover:text-[var(--acc)]"
                                  style={{ fontFamily: "'Space Grotesk', sans-serif", color: INK, ['--acc' as string]: th.accent2 }}
                                >
                                  {p.fighter_b}
                                </Link>
                                <div
                                  className="text-2xl font-bold tabular-nums text-right"
                                  style={{ color: !aWins ? tierColor : '#a8a29e', fontFamily: "'Space Grotesk', sans-serif" }}
                                >
                                  {(bProb * 100).toFixed(0)}%
                                </div>
                              </div>
                            </div>

                            {/* PROBABILITY BAR */}
                            <div
                              className="h-3 w-full overflow-hidden"
                              style={{ background: '#e7e2d6', border: '1.5px solid ' + INK }}
                            >
                              <div
                                className="h-full transition-all duration-700"
                                style={{ width: `${aProb * 100}%`, background: aWins ? tierColor : '#a8a29e' }}
                              />
                            </div>

                            {/* PICK */}
                            <div className="flex items-center justify-between mt-4">
                              <div className="text-xs" style={{ color: th.sub }}>
                                Model pick:{' '}
                                <span className="font-bold" style={{ color: tierColor }}>
                                  {p.predicted_winner}
                                </span>
                                {' '}({(winnerProb * 100).toFixed(0)}% → {(loserProb * 100).toFixed(0)}%)
                              </div>
                              <Link
                                href={`/compare/${encodeURIComponent(p.fighter_a)}/${encodeURIComponent(p.fighter_b)}`}
                                className="text-[10px] tracking-widest uppercase font-bold transition-colors hover:text-[var(--acc)]"
                                style={{ color: INK, ['--acc' as string]: th.accent }}
                              >
                                Compare →
                              </Link>
                            </div>

                            {/* RESULT (if known) */}
                            {p.actual_winner && (
                              <div
                                className="mt-3 pt-3 text-xs font-bold"
                                style={{
                                  borderTop: '2px solid ' + INK,
                                  color:
                                    p.prediction_correct === true
                                      ? POP.teal
                                      : p.prediction_correct === false
                                      ? POP.redDeep
                                      : th.sub,
                                }}
                              >
                                Result: {p.actual_winner}
                                {p.actual_method && ` via ${p.actual_method}`}
                                {p.actual_round && ` R${p.actual_round}`}
                                {p.prediction_correct === true && ' ✓'}
                                {p.prediction_correct === false && ' ✗'}
                              </div>
                            )}
                          </div>
                        </div>
                      </Reveal>
                    )
                  })}
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}
