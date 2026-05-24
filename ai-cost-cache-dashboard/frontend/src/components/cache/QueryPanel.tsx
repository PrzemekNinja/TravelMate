import { useState } from 'react'
import { Search } from 'lucide-react'

const SAMPLE_QUERIES = [
  "What are the top attractions in Prague?",
  "How to get around Rome by public transport?",
  "Best food to try in Tokyo",
  "When is the best time to visit Barcelona?",
  "Prague beer culture and best pubs",
]

const MODELS = [
  { id: 'gpt-4o-mini', label: 'GPT-4o-mini' },
  { id: 'gpt-4.1', label: 'GPT-4.1' },
  { id: 'claude-haiku', label: 'Claude Haiku' },
  { id: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' },
  { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  { id: 'llama-3', label: 'Llama 3' },
]

interface QueryPanelProps {
  onQuery: (query: string, threshold: number, modelId: string) => void
  loading: boolean
}

export function QueryPanel({ onQuery, loading }: QueryPanelProps) {
  const [query, setQuery] = useState('')
  const [threshold, setThreshold] = useState(0.85)
  const [modelId, setModelId] = useState('gpt-4o-mini')

  const handleSubmit = () => {
    if (!query.trim()) return
    onQuery(query, threshold, modelId)
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Query Cache</h2>

      {/* Sample queries */}
      <div>
        <p className="text-xs text-gray-500 mb-2">Try a sample:</p>
        <div className="flex flex-wrap gap-1.5">
          {SAMPLE_QUERIES.map(q => (
            <button
              key={q}
              onClick={() => setQuery(q)}
              className="rounded-full border border-gray-700 bg-gray-800 px-2.5 py-1 text-xs text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
            >
              {q.length > 35 ? q.slice(0, 35) + '…' : q}
            </button>
          ))}
        </div>
      </div>

      {/* Query input */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1.5">Your query</label>
        <textarea
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="e.g. What are the best restaurants in Prague?"
          className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 resize-none"
          rows={3}
          onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) handleSubmit() }}
        />
      </div>

      {/* Threshold slider */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-medium text-gray-400">Similarity threshold</label>
          <span className="text-xs font-mono font-semibold text-emerald-400">{threshold.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0.5}
          max={1.0}
          step={0.01}
          value={threshold}
          onChange={e => setThreshold(parseFloat(e.target.value))}
          className="w-full accent-emerald-500"
        />
        <div className="flex justify-between text-xs text-gray-600 mt-0.5">
          <span>0.50 (loose)</span>
          <span>1.00 (exact)</span>
        </div>
      </div>

      {/* Reference model */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1.5">Reference model (for savings calc)</label>
        <select
          value={modelId}
          onChange={e => setModelId(e.target.value)}
          className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
        >
          {MODELS.map(m => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </select>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading || !query.trim()}
        className="flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            Searching...
          </>
        ) : (
          <>
            <Search className="h-4 w-4" />
            Search Cache
          </>
        )}
      </button>
    </div>
  )
}
