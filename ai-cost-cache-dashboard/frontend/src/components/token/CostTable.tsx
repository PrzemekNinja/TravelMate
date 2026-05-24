import { TrendingDown } from 'lucide-react'
import type { CostEntry } from '../../lib/types'

interface CostTableProps {
  costs: CostEntry[]
}

export function CostTable({ costs }: CostTableProps) {
  const maxCost = Math.max(...costs.map(c => c.total_cost_usd))
  const minCost = Math.min(...costs.map(c => c.total_cost_usd))

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Detailed Breakdown</h2>
      <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-950/50">
                <th className="px-4 py-3 text-left font-medium text-gray-400">Provider / Model</th>
                <th className="px-4 py-3 text-right font-medium text-gray-400">$/M in</th>
                <th className="px-4 py-3 text-right font-medium text-gray-400">$/M out</th>
                <th className="px-4 py-3 text-right font-medium text-gray-400">Input cost</th>
                <th className="px-4 py-3 text-right font-medium text-gray-400">Output cost</th>
                <th className="px-4 py-3 text-right font-medium text-gray-400">Total</th>
                <th className="px-4 py-3 text-right font-medium text-gray-400">Savings</th>
              </tr>
            </thead>
            <tbody>
              {costs.map((c) => {
                const isCheapest = c.total_cost_usd === minCost
                const isMostExpensive = c.total_cost_usd === maxCost
                return (
                  <tr
                    key={c.model_id}
                    className={`border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors ${
                      isCheapest ? 'bg-emerald-500/5' : isMostExpensive ? 'bg-red-500/5' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: c.color }}
                        />
                        <div>
                          <div className="font-medium text-gray-200">{c.model}</div>
                          <div className="text-gray-500">{c.provider}</div>
                        </div>
                        {isCheapest && (
                          <span className="ml-1 rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/30">
                            CHEAPEST
                          </span>
                        )}
                        {isMostExpensive && (
                          <span className="ml-1 rounded-full bg-red-500/20 px-1.5 py-0.5 text-[10px] font-medium text-red-400 border border-red-500/30">
                            PRICIEST
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-400">${c.input_price_per_million_usd}</td>
                    <td className="px-4 py-3 text-right text-gray-400">${c.output_price_per_million_usd}</td>
                    <td className="px-4 py-3 text-right text-blue-400">${c.input_cost_usd.toFixed(6)}</td>
                    <td className="px-4 py-3 text-right text-emerald-400">${c.output_cost_usd.toFixed(6)}</td>
                    <td className="px-4 py-3 text-right font-semibold text-white">${c.total_cost_usd.toFixed(6)}</td>
                    <td className="px-4 py-3 text-right">
                      {c.savings_vs_most_expensive_pct > 0 ? (
                        <span className="flex items-center justify-end gap-1 text-green-400">
                          <TrendingDown className="h-3 w-3" />
                          {c.savings_vs_most_expensive_pct.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-gray-600">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
