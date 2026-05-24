import { useEffect, useState, useRef } from 'react'
import { FolderOpen, MapPin, Users, ChevronRight, RefreshCw, Zap } from 'lucide-react'
import { runsApi } from '../../lib/api'
import type { TravelMateRun } from '../../lib/types'

interface RunPickerProps {
  onSelect: (run: TravelMateRun) => void
}

export function RunPicker({ onSelect }: RunPickerProps) {
  const [runs, setRuns] = useState<TravelMateRun[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [newLiveId, setNewLiveId] = useState<string | null>(null)
  const prevLiveIds = useRef<Set<string>>(new Set())

  const load = async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const data = await runsApi.list()
      setRuns(data)

      // Detect newly live-pushed runs
      const currentLiveIds = new Set(data.filter(r => r.live).map(r => r.id))
      const newIds = [...currentLiveIds].filter(id => !prevLiveIds.current.has(id))
      if (newIds.length > 0) {
        setNewLiveId(newIds[0])
        // Auto-open picker when a new live run arrives
        setOpen(true)
        setTimeout(() => setNewLiveId(null), 8000)
      }
      prevLiveIds.current = currentLiveIds
    } catch {
      setRuns([])
    } finally {
      if (!silent) setLoading(false)
    }
  }

  // Initial load
  useEffect(() => { load() }, [])

  // Poll every 5 seconds for live pushes
  useEffect(() => {
    const interval = setInterval(() => load(true), 5000)
    return () => clearInterval(interval)
  }, [])

  const liveRuns = runs.filter(r => r.live)
  const fsRuns = runs.filter(r => !r.live)

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <div className="h-3 w-3 animate-spin rounded-full border border-gray-600 border-t-gray-400" />
        Scanning TravelMate runs...
      </div>
    )
  }

  if (runs.length === 0) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-600">
        <FolderOpen className="h-3.5 w-3.5" />
        No TravelMate runs found yet
      </div>
    )
  }

  return (
    <div className="relative">
      <div className="flex items-center gap-2">
        <button
          onClick={() => setOpen(!open)}
          className="relative flex items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-500/20 transition-colors"
        >
          <FolderOpen className="h-3.5 w-3.5" />
          Load from TravelMate runs
          <span className="rounded-full bg-blue-500/20 px-1.5 py-0.5 text-[10px]">{runs.length}</span>
          {liveRuns.length > 0 && (
            <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-white">
              {liveRuns.length}
            </span>
          )}
        </button>
        <button onClick={() => load()} className="text-gray-600 hover:text-gray-400 transition-colors" title="Refresh">
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
        {liveRuns.length > 0 && (
          <span className="flex items-center gap-1 text-xs text-emerald-400 animate-pulse">
            <Zap className="h-3 w-3" />
            {liveRuns.length} live
          </span>
        )}
      </div>

      {open && (
        <div className="absolute top-full left-0 mt-1 z-50 w-96 rounded-xl border border-gray-700 bg-gray-900 shadow-2xl overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-800 flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              TravelMate Runs
            </p>
            <span className="text-xs text-gray-600">{runs.length} total</span>
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-gray-800">
            {/* Live runs section */}
            {liveRuns.length > 0 && (
              <>
                <div className="px-3 py-1.5 bg-emerald-500/5 border-b border-emerald-500/20">
                  <p className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                    <Zap className="h-3 w-3" /> Live — auto-pushed from TravelMate
                  </p>
                </div>
                {liveRuns.map(run => (
                  <RunRow
                    key={run.id}
                    run={run}
                    isNew={run.id === newLiveId}
                    onSelect={() => { onSelect(run); setOpen(false) }}
                  />
                ))}
              </>
            )}

            {/* File-system runs section */}
            {fsRuns.length > 0 && (
              <>
                {liveRuns.length > 0 && (
                  <div className="px-3 py-1.5 bg-gray-800/50">
                    <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                      From output/ folder
                    </p>
                  </div>
                )}
                {fsRuns.map(run => (
                  <RunRow
                    key={run.id}
                    run={run}
                    isNew={false}
                    onSelect={() => { onSelect(run); setOpen(false) }}
                  />
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Backdrop */}
      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
      )}
    </div>
  )
}

function RunRow({ run, isNew, onSelect }: { run: TravelMateRun; isNew: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-full flex items-start gap-3 px-3 py-3 hover:bg-gray-800 transition-colors text-left ${
        isNew ? 'bg-emerald-500/10' : ''
      }`}
    >
      <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${
        run.live
          ? 'bg-emerald-600/20 border-emerald-500/30'
          : 'bg-blue-600/20 border-blue-500/20'
      }`}>
        {run.live
          ? <Zap className="h-3.5 w-3.5 text-emerald-400" />
          : <MapPin className="h-3.5 w-3.5 text-blue-400" />
        }
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">{run.destination}</span>
          <span className="text-xs text-gray-500">{run.days}d · {run.budget} · {run.pace}</span>
          {isNew && (
            <span className="rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/30">
              NEW
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-600">
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            {run.participants}
          </span>
          {run.interests.length > 0 && (
            <span className="truncate">{run.interests.slice(0, 2).join(', ')}{run.interests.length > 2 ? '…' : ''}</span>
          )}
        </div>
        <p className="text-xs text-gray-600 mt-0.5 truncate">{run.id}</p>
      </div>
      <ChevronRight className="h-4 w-4 text-gray-600 shrink-0 mt-1" />
    </button>
  )
}
