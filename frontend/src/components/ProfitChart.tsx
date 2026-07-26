'use client'

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts'
import { POP, INK } from '@/lib/pop'

export interface ProfitPoint {
  date: string
  cumulative: number
}

interface TooltipProps {
  active?: boolean
  payload?: { value: number; payload: ProfitPoint }[]
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload || !payload.length) return null
  const p = payload[0].payload
  return (
    <div style={{ background: '#141418', border: `2px solid ${POP.orange}`, padding: '8px 12px' }}>
      <div style={{ color: '#a1a1aa', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{p.date}</div>
      <div style={{ color: '#fafafa', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 18 }}>
        {p.cumulative >= 0 ? '+' : ''}{p.cumulative.toFixed(1)}u
      </div>
    </div>
  )
}

export default function ProfitChart({ data }: { data: ProfitPoint[] }) {
  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="profitFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={POP.orange} stopOpacity={0.5} />
              <stop offset="100%" stopColor={POP.orange} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1e1e24" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: '#71717a', fontSize: 10 }} tickLine={false} axisLine={{ stroke: '#2a2a30' }} minTickGap={48} />
          <YAxis tick={{ fill: '#71717a', fontSize: 10 }} tickLine={false} axisLine={false} width={48} tickFormatter={(v) => `${v}u`} />
          <ReferenceLine y={0} stroke="#3f3f46" strokeDasharray="3 3" />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: POP.orange, strokeWidth: 1 }} />
          <Area
            type="monotone"
            dataKey="cumulative"
            stroke={POP.orange}
            strokeWidth={2.5}
            fill="url(#profitFill)"
            dot={false}
            activeDot={{ r: 4, fill: POP.orange, stroke: INK, strokeWidth: 2 }}
            isAnimationActive
            animationDuration={1400}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
