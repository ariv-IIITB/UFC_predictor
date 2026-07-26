import { createServerClient } from '@/lib/supabase'
import { Suspense } from 'react'
import FightsTable from './FightsTable'
import PopHeader from '@/components/PopHeader'
import { PAGE_THEME } from '@/lib/pop'
import type { FightHistory } from '@/lib/types'

const th = PAGE_THEME.fights

export const revalidate = 3600

const PAGE_SIZE = 50

interface PageProps {
  searchParams: Promise<{
    page?: string
    sort?: string
    dir?: string
    division?: string
    betOnly?: string
    q?: string
  }>
}

async function getData(params: Awaited<PageProps['searchParams']>) {
  const db = createServerClient()
  const page = Math.max(1, Number(params.page ?? 1))
  const sort = params.sort ?? 'fight_date'
  const dir = (params.dir ?? 'desc') as 'asc' | 'desc'
  const division = params.division ?? ''
  const betOnly = params.betOnly === 'true'
  const q = params.q ?? ''

  let query = db.from('fight_history').select('*', { count: 'exact' })

  if (division) query = query.eq('division_norm', division)
  if (betOnly) query = query.eq('bet_placed', true)
  if (q) query = query.or(`a_fighter_name.ilike.%${q}%,b_fighter_name.ilike.%${q}%`)

  const from = (page - 1) * PAGE_SIZE
  const to = from + PAGE_SIZE - 1

  const { data, count } = await query
    .order(sort, { ascending: dir === 'asc' })
    .range(from, to)

  return {
    rows: (data ?? []) as FightHistory[],
    total: count ?? 0,
    page,
    sort,
    dir,
    division,
    betOnly,
  }
}

export default async function FightsPage({ searchParams }: PageProps) {
  const params = await searchParams
  const data = await getData(params)

  return (
    <div className="pt-14 min-h-screen" style={{ background: th.bg }}>
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="mb-10">
          <PopHeader label="Model · Walk-Forward" title="Fight History" th={th} />
          <p className="text-sm max-w-lg mt-6 font-medium" style={{ color: th.sub }}>
            Every fight the model analysed since 2021 — odds, model probability, edge, and P/L per bet.
            Click any row to compare fighters head-to-head.
          </p>
        </div>

        <Suspense fallback={<div className="text-xs tracking-widest uppercase font-bold" style={{ color: th.sub }}>Loading...</div>}>
          <FightsTable
            rows={data.rows}
            total={data.total}
            page={data.page}
            pageSize={PAGE_SIZE}
            sort={data.sort}
            dir={data.dir}
            division={data.division}
            betOnly={data.betOnly}
          />
        </Suspense>
      </div>
    </div>
  )
}
