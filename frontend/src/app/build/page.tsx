import { createServerClient } from '@/lib/supabase'
import PopHeader from '@/components/PopHeader'
import Reveal from '@/components/Reveal'
import MatchupBuilder from '@/components/MatchupBuilder'
import { PAGE_THEME, INK, hard } from '@/lib/pop'

export const revalidate = 3600

const th = { ...PAGE_THEME.compare } // magenta accent, cream bg

async function getFighters() {
  const db = createServerClient()
  const { data } = await db
    .from('fighters')
    .select('fighter_name, division_norm')
    .order('overall', { ascending: false })
    .limit(1500)
  // De-dupe by name (a fighter can appear across multiple pre-fight snapshots)
  const seen = new Set<string>()
  const out: { name: string; division: string | null }[] = []
  for (const row of data ?? []) {
    const r = row as { fighter_name: string | null; division_norm: string | null }
    if (!r.fighter_name || seen.has(r.fighter_name)) continue
    seen.add(r.fighter_name)
    out.push({ name: r.fighter_name, division: r.division_norm })
  }
  return out
}

export default async function BuildPage() {
  const fighters = await getFighters()

  return (
    <div className="pt-14 min-h-screen" style={{ background: th.bg }}>
      <div className="mx-auto max-w-4xl px-6 py-16">
        <PopHeader label="Fantasy matchup builder" title="Build a Fight" th={th} />

        <Reveal delay={0.1} className="mt-6 mb-12">
          <p className="text-sm max-w-xl leading-relaxed" style={{ color: th.sub }}>
            Pick any two fighters and the model estimates a win probability on demand from current
            ratings, ELO, style matchup and momentum. {fighters.length} fighters available.
          </p>
        </Reveal>

        <Reveal delay={0.15}>
          <div className="bg-white p-6 md:p-8" style={{ border: `3px solid ${INK}`, ...hard(INK, 8, 8) }}>
            <MatchupBuilder fighters={fighters} />
          </div>
        </Reveal>
      </div>
    </div>
  )
}
