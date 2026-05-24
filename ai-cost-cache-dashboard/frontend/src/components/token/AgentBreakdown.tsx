import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, Cell,
} from 'recharts'
import { Activity, Cpu } from 'lucide-react'
import { runsApi } from '../../lib/api'
import type { PipelineTokenUsage } from '../../lib/types'

const AGENT_COLORS: Record<string, string> = {
  profile_agent:      '#3b82f6',
  transport_agent:    '#10b981',
  geo_agent:          '#f59e0b',
  itinerary_agent:    '#8b5cf6',
  verification_agent: '#ef4444',
  formatter_agent:    '#ec4899',
}

const AGENT_LABELS: Record<string, string> = {
  profile_agent:      'Profile',
  transport_agent:    'Transport',
  geo_agent:          'Geo',
  itinerary_agent:    'Itinerary',
  verification_agent: 'Verification',
  formatter_agent:    'Formatter',
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const d = payload[0].payload
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-3 shadow-xl text-xs">
        <p className="font-semibold text-white mb-2">{AGENT_LABELS[d.agent] || d.agent}</p>
        <div className="space-y-1 text-gray-300">
          <div className="flex justify-between gap-4">
            <span>Input:</span>
            <span className="text-blue-400">{d.input_tokens.toLocaleString()}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span>Output:</span>
            <span className="text-emerald-400">{d.output_tokens.toLocaleString()}</span>
          </div>
          <div className="flex justify-between gap-4 border-t border-gray-700 pt-1">
            <span className="font-semibold text-white">Total:</span>
            <span className="font-semibold text-white">{d.total_tokens.toLocaleString()}</span>
          </div>
          <div className="flex justify-between gap-4 text-gray-500">
            <span>% of pipeline:</span>
            <span>{d.pct.toFixed(1)}%</span>
          </div>
        </div>
      </div>
    )
  }
  return null
}

interface AgentBreakdownProps {
  runId: string | null
  // Can also accept inline data (from live push)
  inlineData?: PipelineTokenUsage | null
}

export function AgentBreakdown({ runId, inlineData }: AgentBreakdownProps) {
  const [data, setData] = useState<PipelineTokenUsage | null>(inlineData || null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (inlineData) { setData(inlineData); return }
    if (!runId) return
    setLoading(true)
    setError(null)
    runsApi.getTokens(runId)
      .then(d => setData(d))
      .catch(() => setError('No token data for this run yet. Run a new trip to see real counts.'))
      .finally(() => setLoading(false))
  }, [runId, inlineData])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500 py-4">
        <div className="h-3 w-3 animate-spin rounded-full border border-gray-600 border-t-gray-400" />
        Loading token breakdown...
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900/50 px-4 py-3 text-xs text-gray-500">
        {error}
      </div>
    )
  }

  if (!data) return null

  const totalTokens = data.total_tokens || 1
  const chartData = data.agents.map(a => ({
    ...a,
    label: AGENT_LABELS[a.agent] || a.agent,
    pct: (a.total_tokens / totalTokens) * 100,
  }))

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Real Pipeline Token Usage
        </h2>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Cpu className="h-3.5 w-3.5" />
          {data.provider} · {data.model_name}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Total Input', value: data.total_input_tokens, color: 'border-blue-500/20 text-blue-400' },
          { label: 'Total Output', value: data.total_output_tokens, color: 'border-emerald-500/20 text-emerald-400' },
          { label: 'Grand Total', value: data.total_tokens, color: 'border-purple-500/20 text-purple-400' },
        ].map(card => (
          <div key={card.label} className={`rounded-xl border bg-gray-900 p-3 ${card.color.split(' ')[0]}`}>
            <div className="text-xs text-gray-500 mb-1">{card.label}</div>
            <div className={`text-xl font-bold ${card.color.split(' ')[1]}`}>
              {card.value.toLocaleString()}
            </div>
            <div className="text-xs text-gray-600">tokens</div>
          </div>
        ))}
      </div>

      {/* Stacked bar chart per agent */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
        <p className="text-xs text-gray-500 mb-3">Tokens per agent (input + output)</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Legend
              wrapperStyle={{ fontSize: '11px', color: '#9ca3af' }}
              formatter={(value) => value === 'input_tokens' ? 'Input' : 'Output'}
            />
            <Bar dataKey="input_tokens" name="input_tokens" stackId="a" radius={[0,0,0,0]}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.agent}
                  fill={AGENT_COLORS[entry.agent] || '#6b7280'}
                  fillOpacity={0.6}
                />
              ))}
            </Bar>
            <Bar dataKey="output_tokens" name="output_tokens" stackId="a" radius={[4,4,0,0]}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.agent}
                  fill={AGENT_COLORS[entry.agent] || '#6b7280'}
                  fillOpacity={1}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Per-agent table */}
      <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-950/50">
              <th className="px-4 py-2.5 text-left font-medium text-gray-400">Agent</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-400">Input</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-400">Output</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-400">Total</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-400">% pipeline</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map(a => (
              <tr key={a.agent} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: AGENT_COLORS[a.agent] || '#6b7280' }}
                    />
                    <span className="font-medium text-gray-200">{a.label}</span>
                  </div>
                </td>
                <td className="px-4 py-2.5 text-right text-blue-400">{a.input_tokens.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-right text-emerald-400">{a.output_tokens.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-right font-semibold text-white">{a.total_tokens.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-gray-800 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${a.pct}%`,
                          backgroundColor: AGENT_COLORS[a.agent] || '#6b7280',
                        }}
                      />
                    </div>
                    <span className="text-gray-400 w-10 text-right">{a.pct.toFixed(1)}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
