import { Search, CheckCircle, XCircle, TrendingUp, DollarSign } from 'lucide-react'
import type { CacheStats } from '../../lib/types'

interface StatsBarProps {
  stats: CacheStats | null
}

function StatPill({ icon, label, value, color }: {
  icon: React.ReactNode
  label: string
  value: string | number
  color: string
}) {
  return (
    <div className={`flex items-center gap-2 rounded-lg border bg-gray-900 px-4 py-3 ${color}`}>
      <div className="text-gray-400">{icon}</div>
      <div>
        <div className="text-lg font-bold text-white">{value}</div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    </div>
  )
}

export function StatsBar({ stats }: StatsBarProps) {
  if (!stats) return null

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
      <StatPill
        icon={<Search className="h-4 w-4" />}
        label="Total queries"
        value={stats.total_queries}
        color="border-gray-700"
      />
      <StatPill
        icon={<CheckCircle className="h-4 w-4 text-emerald-400" />}
        label="Cache hits"
        value={stats.total_hits}
        color="border-emerald-500/20"
      />
      <StatPill
        icon={<XCircle className="h-4 w-4 text-red-400" />}
        label="Cache misses"
        value={stats.total_misses}
        color="border-red-500/20"
      />
      <StatPill
        icon={<TrendingUp className="h-4 w-4 text-blue-400" />}
        label="Hit rate"
        value={`${stats.hit_rate_pct}%`}
        color="border-blue-500/20"
      />
      <StatPill
        icon={<DollarSign className="h-4 w-4 text-yellow-400" />}
        label="Total savings"
        value={`$${stats.cumulative_savings_usd.toFixed(6)}`}
        color="border-yellow-500/20"
      />
    </div>
  )
}
