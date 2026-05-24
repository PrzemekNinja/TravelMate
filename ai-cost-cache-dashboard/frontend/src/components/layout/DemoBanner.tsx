import { AlertTriangle } from 'lucide-react'

export function DemoBanner() {
  return (
    <div className="border-b border-amber-500/30 bg-amber-500/10 px-4 py-2">
      <div className="mx-auto max-w-7xl flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
        <p className="text-xs text-amber-300">
          <span className="font-semibold">Demo Mode</span> — using pre-computed mock embeddings.
          Token counting is real (tiktoken). Set <code className="bg-amber-500/20 px-1 rounded">DEMO_MODE=false</code> in backend <code className="bg-amber-500/20 px-1 rounded">.env</code> for live sentence-transformer embeddings.
        </p>
      </div>
    </div>
  )
}
