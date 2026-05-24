import { CheckCircle, XCircle } from 'lucide-react'
import type { HistoryItem } from '../../lib/types'

interface QueryHistoryProps {
  history: HistoryItem[]
}

export function QueryHistory({ history }: QueryHistoryProps) {
  if (history.length === 0) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900 p-4 text-center">
        <p className="text-xs text-gray-500">No queries yet — try searching the cache</p>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
        Query History <span className="text-gray-600 font-normal">(last 20)</span>
      </h2>
      <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
        <div className="divide-y divide-gray-800">
          {history.map((item, i) => (
            <div key={i} className="flex items-start gap-3 px-4 py-3 hover:bg-gray-800/30 transition-colors">
              <div className="mt-0.5 shrink-0">
                {item.hit ? (
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-300 truncate">{item.query}</p>
                {item.matched_key && (
                  <p className="text-xs text-gray-600 truncate mt-0.5">→ {item.matched_key}</p>
                )}
              </div>
              <div className="shrink-0 text-right">
                <div className={`text-xs font-mono font-semibold ${item.hit ? 'text-emerald-400' : 'text-gray-600'}`}>
                  {Math.round(item.similarity * 100)}%
                </div>
                {item.savings_usd > 0 && (
                  <div className="text-xs text-yellow-500">${item.savings_usd.toFixed(6)}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
