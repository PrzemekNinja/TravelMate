import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { SavingsTimelineItem } from '../../lib/types'

interface SavingsChartProps {
  timeline: SavingsTimelineItem[]
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const d = payload[0].payload as SavingsTimelineItem
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-3 shadow-xl text-xs">
        <p className={`font-semibold mb-1 ${d.hit ? 'text-emerald-400' : 'text-red-400'}`}>
          {d.hit ? '✓ Cache Hit' : '✗ Cache Miss'}
        </p>
        <div className="space-y-1 text-gray-300">
          <div className="flex justify-between gap-4">
            <span>Saved this query:</span>
            <span className="text-yellow-400">${d.savings_usd.toFixed(6)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span>Cumulative savings:</span>
            <span className="text-white font-semibold">${d.cumulative_savings_usd.toFixed(6)}</span>
          </div>
        </div>
      </div>
    )
  }
  return null
}

export function SavingsChart({ timeline }: SavingsChartProps) {
  if (timeline.length === 0) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 text-center">
        <p className="text-sm text-gray-500">Run some queries to see savings accumulate</p>
      </div>
    )
  }

  const data = timeline.map((item, i) => ({
    ...item,
    index: i + 1,
  }))

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Cumulative Savings</h2>
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="index"
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={{ stroke: '#374151' }}
              tickLine={false}
              label={{ value: 'Query #', position: 'insideBottom', offset: -2, fill: '#4b5563', fontSize: 10 }}
            />
            <YAxis
              tickFormatter={v => `$${v.toFixed(4)}`}
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={70}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="cumulative_savings_usd"
              stroke="#10b981"
              strokeWidth={2}
              dot={(props: any) => {
                const { cx, cy, payload } = props
                return (
                  <circle
                    key={`dot-${props.index}`}
                    cx={cx}
                    cy={cy}
                    r={4}
                    fill={payload.hit ? '#10b981' : '#ef4444'}
                    stroke="none"
                  />
                )
              }}
              activeDot={{ r: 6, fill: '#10b981' }}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="text-xs text-gray-600 mt-2 text-center">
          Green dots = cache hits (savings), red dots = misses (no savings)
        </p>
      </div>
    </div>
  )
}
