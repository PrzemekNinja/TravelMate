import { AlertTriangle, Clock } from 'lucide-react'
import { InputPanel } from '../components/token/InputPanel'
import { TokenSummary } from '../components/token/TokenSummary'
import { CostChart } from '../components/token/CostChart'
import { CostTable } from '../components/token/CostTable'
import { useTokenAnalysis } from '../hooks/useTokenAnalysis'

export function TokenCost() {
  const { result, loading, error, analyze } = useTokenAnalysis()

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Token Cost Comparison</h1>
        <p className="mt-1 text-sm text-gray-400">
          Paste a TravelMate trip request and response to see how much it would cost across 8 LLM models.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
        {/* Left: Input */}
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <InputPanel onAnalyze={analyze} loading={loading} error={error} />
        </div>

        {/* Right: Results */}
        <div className="flex flex-col gap-6">
          {result ? (
            <>
              {/* Pricing freshness */}
              <div className="flex items-center gap-2">
                {result.pricing_stale ? (
                  <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    Pricing data may be outdated (last updated: {result.pricing_last_updated}). Verify current prices.
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Clock className="h-3.5 w-3.5" />
                    Pricing last updated: {result.pricing_last_updated}
                  </div>
                )}
              </div>

              <TokenSummary
                inputTokens={result.input_tokens}
                outputTokens={result.output_tokens}
                totalTokens={result.total_tokens}
              />

              <CostChart costs={result.costs} />

              <CostTable costs={result.costs} />

              <p className="text-xs text-gray-600">
                * Token counts use tiktoken cl100k_base encoding (GPT-4 compatible). Counts are approximate for non-OpenAI models.
              </p>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-xl border border-gray-800 bg-gray-900/30 p-16 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-600/10 border border-blue-500/20">
                <svg className="h-8 w-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-gray-300 mb-1">Ready to analyze</h3>
              <p className="text-sm text-gray-500 max-w-xs">
                The input panel is pre-loaded with a sample Prague trip. Hit <strong className="text-gray-400">Run Analysis</strong> to see cost comparison across all 8 models.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
