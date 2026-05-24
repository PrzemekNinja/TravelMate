import { useState } from 'react'
import { Plus, Database, X } from 'lucide-react'
import type { CacheEntryItem } from '../../lib/types'

interface CacheEntryListProps {
  entries: CacheEntryItem[]
  onAdd: (key: string, response: string) => Promise<void>
}

export function CacheEntryList({ entries, onAdd }: CacheEntryListProps) {
  const [showForm, setShowForm] = useState(false)
  const [newKey, setNewKey] = useState('')
  const [newResponse, setNewResponse] = useState('')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  const handleAdd = async () => {
    if (!newKey.trim() || !newResponse.trim()) return
    setAdding(true)
    setAddError(null)
    try {
      await onAdd(newKey, newResponse)
      setNewKey('')
      setNewResponse('')
      setShowForm(false)
    } catch (e: any) {
      setAddError(e.message)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-2">
          <Database className="h-4 w-4" />
          Cache Entries
          <span className="rounded-full bg-gray-700 px-2 py-0.5 text-xs font-normal text-gray-400">
            {entries.length}
          </span>
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500/20 transition-colors"
        >
          {showForm ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
          {showForm ? 'Cancel' : 'Add Entry'}
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="mb-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 space-y-2">
          <input
            value={newKey}
            onChange={e => setNewKey(e.target.value)}
            placeholder="Query key (e.g. 'Best hotels in Lisbon?')"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
          />
          <textarea
            value={newResponse}
            onChange={e => setNewResponse(e.target.value)}
            placeholder="Cached response text..."
            className="w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 resize-none"
            rows={3}
          />
          {addError && <p className="text-xs text-red-400">{addError}</p>}
          <button
            onClick={handleAdd}
            disabled={adding || !newKey.trim() || !newResponse.trim()}
            className="w-full rounded-lg bg-emerald-600 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 transition-colors"
          >
            {adding ? 'Adding...' : 'Add to Cache'}
          </button>
        </div>
      )}

      {/* Entry list */}
      <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
        {entries.map(entry => (
          <div
            key={entry.id}
            className="rounded-lg border border-gray-800 bg-gray-900 px-3 py-2.5 hover:border-gray-700 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs font-medium text-gray-300 leading-snug">{entry.key}</p>
              {entry.hit_count > 0 && (
                <span className="shrink-0 rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400">
                  {entry.hit_count}×
                </span>
              )}
            </div>
            <p className="text-xs text-gray-600 mt-1 leading-relaxed line-clamp-2">{entry.response_preview}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
