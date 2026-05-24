import { Hash, ArrowDown, ArrowUp } from 'lucide-react'

interface TokenSummaryProps {
  inputTokens: number
  outputTokens: number
  totalTokens: number
}

function StatCard({ label, value, icon, color }: {
  label: string
  value: number
  icon: React.ReactNode
  color: string
}) {
  return (
    <div className={`rounded-xl border bg-gray-900 p-4 ${color}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">{label}</span>
        <div className="text-gray-500">{icon}</div>
      </div>
      <div className="text-2xl font-bold text-white animate-count">
        {value.toLocaleString()}
      </div>
      <div className="text-xs text-gray-500 mt-1">tokens</div>
    </div>
  )
}

export function TokenSummary({ inputTokens, outputTokens, totalTokens }: TokenSummaryProps) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">Token Usage</h2>
      <div className="grid grid-cols-3 gap-3">
        <StatCard
          label="Input"
          value={inputTokens}
          icon={<ArrowDown className="h-4 w-4" />}
          color="border-blue-500/20"
        />
        <StatCard
          label="Output"
          value={outputTokens}
          icon={<ArrowUp className="h-4 w-4" />}
          color="border-emerald-500/20"
        />
        <StatCard
          label="Total"
          value={totalTokens}
          icon={<Hash className="h-4 w-4" />}
          color="border-purple-500/20"
        />
      </div>
    </div>
  )
}
