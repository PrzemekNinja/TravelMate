import { CheckCircle, XCircle, DollarSign, AlertCircle } from 'lucide-react'
import type { QueryResult } from '../../lib/types'

interface HitMissBadgeProps {
  result: QueryResult
}

export function HitMissBadge({ result }: HitMissBadgeProps) {
  const similarityPct = Math.round(result.similarity * 100)

  return (
    <div className={`rounded-xl border p-5 ${
      result.hit
        ? 'border-emerald-500/30 bg-emerald-500/5 glow-green'
        : 'border-red-500/30 bg-red-500/5 glow-red'
    }`}>
      {/* Badge header */}
      <div className="flex items-center justify-between mb-4">
        <div className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-bold ${
          result.hit
            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
            : 'bg-red-500/20 text-red-400 border border-red-500/30'
        }`}>
          {result.hit ? (
            <><CheckCircle className="h-4 w-4" /> CACHE HIT</>
          ) : (
            <><XCircle className="h-4 w-4" /> CACHE MISS</>
          )}
        </div>

        {/* Similarity gauge */}
        <div className="text-right">
          <div className="text-2xl font-bold text-white">{similarityPct}%</div>
          <div className="text-xs text-gray-500">similarity</div>
        </div>
      </div>

      {/* Similarity bar */}
      <div className="mb-4">
        <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              result.hit ? 'bg-emerald-500' : 'bg-red-500'
            }`}
            style={{ width: `${similarityPct}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-600 mt-1">
          <span>0%</span>
          <span className={`font-medium ${result.hit ? 'text-emerald-400' : 'text-red-400'}`}>
            Threshold: {Math.round(result.threshold * 100)}%
          </span>
          <span>100%</span>
        </div>
      </div>

      {result.hit && result.matched_entry ? (
        <>
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-3 mb-3">
            <p className="text-xs font-medium text-gray-400 mb-1">Matched entry:</p>
            <p className="text-sm font-semibold text-white mb-2">"{result.matched_entry.key}"</p>
            <p className="text-xs text-gray-400 leading-relaxed">{result.matched_entry.response_preview}</p>
          </div>
          <div className="flex items-center gap-2 text-sm text-emerald-400">
            <DollarSign className="h-4 w-4" />
            <span>Saved <strong>${result.savings_usd.toFixed(6)}</strong> by using cache instead of LLM call</span>
          </div>
        </>
      ) : (
        <>
          <div className="flex items-start gap-2 text-sm text-gray-400 mb-3">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-400" />
            <span>No cache entry found above threshold. A full LLM call would be required.</span>
          </div>
          {result.closest_miss && (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-3">
              <p className="text-xs text-gray-500 mb-1">Closest non-matching entry ({Math.round(result.closest_miss.similarity * 100)}% similar):</p>
              <p className="text-xs text-gray-400">"{result.closest_miss.key}"</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
