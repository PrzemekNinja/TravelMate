import { StatsBar } from '../components/cache/StatsBar'
import { QueryPanel } from '../components/cache/QueryPanel'
import { HitMissBadge } from '../components/cache/HitMissBadge'
import { CacheEntryList } from '../components/cache/CacheEntryList'
import { SavingsChart } from '../components/cache/SavingsChart'
import { QueryHistory } from '../components/cache/QueryHistory'
import { useCacheQuery } from '../hooks/useCacheQuery'

export function SemanticCache() {
  const { entries, stats, history, timeline, queryResult, loading, error, query, addEntry } = useCacheQuery()

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Semantic Cache Showcase</h1>
        <p className="mt-1 text-sm text-gray-400">
          Demonstrates how a knowledge cache eliminates redundant LLM calls using semantic similarity matching.
        </p>
      </div>

      {/* Stats bar */}
      <div className="mb-6">
        <StatsBar stats={stats} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
        {/* Left column */}
        <div className="flex flex-col gap-6">
          {/* Query panel */}
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <QueryPanel onQuery={query} loading={loading} />
            {error && (
              <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                {error}
              </div>
            )}
          </div>

          {/* Cache entries */}
          <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <CacheEntryList entries={entries} onAdd={addEntry} />
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-6">
          {/* Hit/Miss result */}
          {queryResult ? (
            <HitMissBadge result={queryResult} />
          ) : (
            <div className="flex flex-col items-center justify-center rounded-xl border border-gray-800 bg-gray-900/30 p-12 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-600/10 border border-emerald-500/20">
                <svg className="h-8 w-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-gray-300 mb-1">Cache ready</h3>
              <p className="text-sm text-gray-500 max-w-xs">
                {entries.length} entries pre-loaded. Try a sample query or type your own travel question to see semantic matching in action.
              </p>
            </div>
          )}

          {/* Savings chart */}
          <SavingsChart timeline={timeline} />

          {/* Query history */}
          <QueryHistory history={history} />
        </div>
      </div>
    </div>
  )
}
