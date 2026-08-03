'use client'

import { useState, useTransition, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import { cn, fmtDate, fmtOdds, fmtPct } from '@/lib/utils'
import { INK, POP, hard, PAGE_THEME } from '@/lib/pop'
import Reveal from '@/components/Reveal'
import type { FightHistory } from '@/lib/types'

const th = PAGE_THEME.fights

interface Props {
  rows: FightHistory[]
  total: number
  page: number
  pageSize: number
  sort: string
  dir: 'asc' | 'desc'
  division: string
  betOnly: boolean
}

const columns: { key: string; label: string; align?: 'right' }[] = [
  { key: 'fight_date', label: 'Date' },
  { key: 'event_name', label: 'Event' },
  { key: 'a_fighter_name', label: 'Fighter A' },
  { key: 'b_fighter_name', label: 'Fighter B' },
  { key: 'division_norm', label: 'Division' },
  { key: 'predicted_winner', label: 'Pick' },
  { key: 'chosen_model_probability', label: 'Prob', align: 'right' },
  { key: 'chosen_odds_decimal', label: 'Odds', align: 'right' },
  { key: 'edge', label: 'Edge', align: 'right' },
  { key: 'profit_units', label: 'P/L', align: 'right' },
]

export default function FightsTable({ rows, total, page, pageSize, sort, dir, division, betOnly }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [, startTransition] = useTransition()
  const [search, setSearch] = useState(searchParams.get('q') ?? '')

  const push = useCallback((params: Record<string, string>) => {
    const sp = new URLSearchParams(searchParams.toString())
    Object.entries(params).forEach(([k, v]) => {
      if (v) sp.set(k, v)
      else sp.delete(k)
    })
    sp.set('page', '1')
    startTransition(() => router.push(`/fights?${sp.toString()}`))
  }, [searchParams, router])

  function handleSort(col: string) {
    const newDir = sort === col && dir === 'desc' ? 'asc' : 'desc'
    push({ sort: col, dir: newDir })
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    push({ q: search })
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-4">
      {/* FILTERS */}
      <div className="flex flex-wrap gap-3 items-center">
        <form onSubmit={handleSearch} className="flex">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search fighter..."
            className="text-xs font-medium px-4 py-2.5 w-52 focus:outline-none placeholder:text-[#57534e]"
            style={{ background: '#fff', border: '2px solid ' + INK, color: INK }}
          />
          <button
            type="submit"
            className="text-xs font-bold uppercase tracking-widest px-4 py-2.5 hover:brightness-95 transition"
            style={{ background: th.accent, color: INK, border: '2px solid ' + INK, borderLeft: 'none' }}
          >
            Go
          </button>
        </form>

        <button
          onClick={() => push({ betOnly: betOnly ? '' : 'true' })}
          className="text-xs tracking-widest uppercase font-bold px-4 py-2.5 transition hover:brightness-95"
          style={{
            background: betOnly ? th.accent : '#fff',
            color: INK,
            border: '2px solid ' + INK,
          }}
        >
          Bets only
        </button>

        <span className="text-xs font-bold uppercase tracking-widest ml-auto" style={{ color: INK }}>
          {total.toLocaleString()} fights
        </span>
      </div>

      {/* TABLE */}
      <Reveal y={30}>
        <div className="overflow-x-auto" style={{ background: '#fff', border: '3px solid ' + INK, ...hard(INK, 6, 6) }}>
          <table className="w-full text-xs">
<thead>
              <tr style={{ background: th.accent, borderBottom: '3px solid ' + INK }}>
                {columns.map(col => {
                  const active = sort === col.key
                  return (
                    <th
                      key={col.key}
                      className={cn(
                        'px-4 py-3 text-left tracking-widest uppercase font-bold cursor-pointer select-none whitespace-nowrap',
                        col.align === 'right' && 'text-right'
                      )}
                      style={{ color: INK }}
                      onClick={() => handleSort(col.key)}
                    >
                      <span
                        className="inline-flex items-center gap-1"
                        style={active ? { borderBottom: '2px solid ' + INK, paddingBottom: 1 } : undefined}
                      >
                        {col.label}
                        {active ? (
                          dir === 'desc' ? <ChevronDown size={12} style={{ color: INK }} /> : <ChevronUp size={12} style={{ color: INK }} />
                        ) : (
                          <ChevronsUpDown size={12} className="opacity-40" style={{ color: INK }} />
                        )}
                      </span>
                    </th>
                  )
                })}
                <th className="px-4 py-3 text-left tracking-widest uppercase font-bold" style={{ color: INK }}>Result</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const profit = row.profit_units ?? 0
                const correct = row.predicted_correct
                return (
                  <tr
                    key={row.fight_id}
                    className="hover:bg-[#fff8dc] cursor-pointer transition-colors group"
                    style={{ borderBottom: '2px solid #e7e2d6' }}
                    onClick={() => router.push(`/compare/${encodeURIComponent(row.a_fighter_name)}/${encodeURIComponent(row.b_fighter_name)}`)}
                  >
                    <td className="px-4 py-3 whitespace-nowrap" style={{ color: th.sub }}>{fmtDate(row.fight_date)}</td>
                    <td className="px-4 py-3 max-w-[160px] truncate" style={{ color: INK }}>{row.event_name ?? '—'}</td>
                    <td className="px-4 py-3 font-bold whitespace-nowrap" style={{ color: INK }}>{row.a_fighter_name}</td>
                    <td className="px-4 py-3 font-bold whitespace-nowrap" style={{ color: INK }}>{row.b_fighter_name}</td>
                    <td className="px-4 py-3 whitespace-nowrap" style={{ color: th.sub }}>{row.division_norm ?? '—'}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {row.predicted_winner ? (
                        <span
                          className="inline-block font-bold px-2 py-0.5 text-[11px]"
                          style={{ background: th.accent2, color: '#fff', border: '1.5px solid ' + INK }}
                        >
                          {row.predicted_winner}
                        </span>
                      ) : (
                        <span style={{ color: th.sub }}>—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums whitespace-nowrap" style={{ color: INK }}>{fmtPct(row.chosen_model_probability)}</td>
                    <td className="px-4 py-3 text-right tabular-nums whitespace-nowrap" style={{ color: INK }}>{fmtOdds(row.chosen_odds_decimal)}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-bold whitespace-nowrap">
                      <span style={{ color: row.edge != null && row.edge > 0.05 ? th.accent2 : INK }}>
                        {row.edge != null ? `+${(row.edge * 100).toFixed(1)}%` : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums font-bold whitespace-nowrap">
                      {row.bet_placed
                        ? <span style={{ color: profit >= 0 ? POP.teal : th.accent2 }}>{(profit >= 0 ? '+' : '') + profit.toFixed(2) + 'u'}</span>
                        : <span style={{ color: '#a8a29e' }}>—</span>}
                    </td>
                    <td className="px-4 py-3">
                      {row.bet_placed ? (
                        correct === true ? (
                          <span className="inline-block text-[10px] tracking-widest uppercase font-bold px-2 py-0.5" style={{ background: POP.teal, color: '#fff', border: '1.5px solid ' + INK }}>Win</span>
                        ) : correct === false ? (
                          <span className="inline-block text-[10px] tracking-widest uppercase font-bold px-2 py-0.5" style={{ background: th.accent2, color: '#fff', border: '1.5px solid ' + INK }}>Loss</span>
                        ) : (
                          <span className="text-[10px] tracking-widest uppercase font-bold" style={{ color: th.sub }}>Pending</span>
                        )
                      ) : (
                        <span className="text-[10px] tracking-widest uppercase font-bold" style={{ color: '#a8a29e' }}>No bet</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Reveal>

      {/* PAGINATION */}
      <div className="flex items-center justify-between pt-2">
        <span className="text-xs font-bold uppercase tracking-widest" style={{ color: INK }}>
          Page {page} of {totalPages}
        </span>
        <div className="flex gap-3">
          <button
            disabled={page <= 1}
            onClick={() => push({ page: String(page - 1) })}
            className="text-xs tracking-widest uppercase font-bold px-4 py-2 transition hover:brightness-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
            style={{ background: '#fff', color: INK, border: '2px solid ' + INK, ...(page <= 1 ? {} : hard(INK, 4, 4)) }}
          >
            ← Prev
          </button>
          <button
            disabled={page >= totalPages}
            onClick={() => push({ page: String(page + 1) })}
            className="text-xs tracking-widest uppercase font-bold px-4 py-2 transition hover:brightness-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
            style={{ background: th.accent, color: INK, border: '2px solid ' + INK, ...(page >= totalPages ? {} : hard(INK, 4, 4)) }}
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  )
}
