import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { CostEntry } from '../../lib/types'

interface CostChartProps {
  costs: CostEntry[]
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const d = payload[0].payload as CostEntry
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-3 shadow-xl text-xs">
        <p className="font-semibold text-white mb-2">{d.provider} — {d.model}</p>
        <div className="space-y-1 text-gray-300">
          <div className="flex justify-between gap-4">
            <span>Input cost:</span>
            <span className="text-blue-400">${d.input_cost_usd.toFixed(6)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span>Output cost:</span>
            <span className="text-emerald-400">${d.output_cost_usd.toFixed(6)}</span>
          </div>
          <div className="flex justify-between gap-4 border-t border-gray-700 pt-1 mt-1">
            <span className="font-semibold text-white">Total:</span>
            <span className="font-semibold text-white">${d.total_cost_usd.toFixed(6)}</span>
          </div>
          <div className="flex justify-between gap-4 text-gray-500">
            <span>Savings vs most exp.:</span>
            <span className="text-green-400">{d.savings_vs_most_expensive_pct.toFixed(1)}%</span>
          </div>
        </div>
      </div>
    )
  }
  return null
}

export function CostChart({ costs }: CostChartProps) {
  const data = costs.map(c => ({
    ...c,
    name: c.model,
    value: c.total_cost_usd,
  }))

  const maxCost = Math.max(...costs.map(c => c.total_cost_usd))
  const minCost = Math.min(...costs.map(c => c.total_cost_usd))

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Cost Comparison</h2>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-green-400"></span>
            Cheapest
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-red-400"></span>
            Most expensive
          </span>
        </div>
      </div>
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 0, right: 60, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
            <XAxis
              type="number"
              tickFormatter={v => `$${v.toFixed(4)}`}
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={{ stroke: '#374151' }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={110}
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={28}>
              {data.map((entry, index) => {
                let fill = entry.color
                if (entry.total_cost_usd === minCost) fill = '#10b981'
                if (entry.total_cost_usd === maxCost) fill = '#ef4444'
                return <Cell key={index} fill={fill} fillOpacity={0.85} />
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
