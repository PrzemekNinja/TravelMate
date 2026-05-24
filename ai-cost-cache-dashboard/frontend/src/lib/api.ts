import axios from 'axios'
import type {
  TokenAnalysisResult,
  CacheEntryItem,
  QueryResult,
  CacheStats,
  HistoryItem,
  SavingsTimelineItem,
  HealthResponse,
  TravelMateRun,
} from './types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export const runsApi = {
  list: () =>
    api.get<{ runs: TravelMateRun[] }>('/runs').then(r => r.data.runs),
  get: (id: string) =>
    api.get<TravelMateRun>(`/runs/${id}`).then(r => r.data),
}

export const healthApi = {
  check: () => api.get<HealthResponse>('/health').then(r => r.data),
}

export const tokensApi = {
  analyze: (requestText: string, responseText: string) =>
    api.post<TokenAnalysisResult>('/tokens/analyze', {
      request_text: requestText,
      response_text: responseText,
    }).then(r => r.data),
}

export const cacheApi = {
  getEntries: () =>
    api.get<{ entries: CacheEntryItem[] }>('/cache/entries').then(r => r.data.entries),

  addEntry: (key: string, response: string) =>
    api.post<{ entry: CacheEntryItem }>('/cache/entries', { key, response }).then(r => r.data.entry),

  query: (query: string, threshold: number, referenceModelId: string) =>
    api.post<QueryResult>('/cache/query', {
      query,
      threshold,
      reference_model_id: referenceModelId,
    }).then(r => r.data),

  getStats: () =>
    api.get<CacheStats>('/cache/stats').then(r => r.data),

  getHistory: () =>
    api.get<{ history: HistoryItem[] }>('/cache/history').then(r => r.data.history),

  getSavingsTimeline: () =>
    api.get<{ timeline: SavingsTimelineItem[] }>('/cache/savings-timeline').then(r => r.data.timeline),
}
