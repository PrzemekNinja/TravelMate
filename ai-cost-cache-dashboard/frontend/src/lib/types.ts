export interface CostEntry {
  provider: string
  model: string
  model_id: string
  color: string
  input_price_per_million_usd: number
  output_price_per_million_usd: number
  input_cost_usd: number
  output_cost_usd: number
  total_cost_usd: number
  savings_vs_most_expensive_pct: number
}

export interface TokenAnalysisResult {
  input_tokens: number
  output_tokens: number
  total_tokens: number
  costs: CostEntry[]
  pricing_last_updated: string
  pricing_stale: boolean
}

export interface CacheEntryItem {
  id: string
  key: string
  response: string
  response_preview: string
  created_at: string
  hit_count: number
}

export interface QueryResult {
  hit: boolean
  similarity: number
  threshold: number
  matched_entry: CacheEntryItem | null
  savings_usd: number
  closest_miss: { key: string; similarity: number } | null
}

export interface CacheStats {
  total_entries: number
  total_queries: number
  total_hits: number
  total_misses: number
  hit_rate_pct: number
  cumulative_savings_usd: number
}

export interface HistoryItem {
  query: string
  hit: boolean
  similarity: number
  matched_key: string | null
  timestamp: string
  savings_usd: number
}

export interface SavingsTimelineItem {
  timestamp: string
  savings_usd: number
  cumulative_savings_usd: number
  hit: boolean
}

export interface AgentTokenUsage {
  agent: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
}

export interface PipelineTokenUsage {
  model_name: string
  provider: string
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  agents: AgentTokenUsage[]
}

export interface TravelMateRun {
  id: string
  destination: string
  days: number | string
  budget: string
  pace: string
  participants: number
  interests: string[]
  request_json: string
  itinerary_md: string
  itinerary_preview: string
  live?: boolean
  pushed_at?: string
}

export interface HealthResponse {
  status: string
  demo_mode: boolean
  version: string
}
