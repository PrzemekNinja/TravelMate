import { useState, useEffect, useCallback } from 'react'
import { cacheApi } from '../lib/api'
import type {
  CacheEntryItem,
  QueryResult,
  CacheStats,
  HistoryItem,
  SavingsTimelineItem,
} from '../lib/types'

export function useCacheQuery() {
  const [entries, setEntries] = useState<CacheEntryItem[]>([])
  const [stats, setStats] = useState<CacheStats | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [timeline, setTimeline] = useState<SavingsTimelineItem[]>([])
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshAll = useCallback(async () => {
    try {
      const [e, s, h, t] = await Promise.all([
        cacheApi.getEntries(),
        cacheApi.getStats(),
        cacheApi.getHistory(),
        cacheApi.getSavingsTimeline(),
      ])
      setEntries(e)
      setStats(s)
      setHistory(h)
      setTimeline(t)
    } catch (e: any) {
      console.error('Failed to refresh cache data', e)
    }
  }, [])

  useEffect(() => {
    refreshAll()
  }, [refreshAll])

  const query = async (queryText: string, threshold: number, referenceModelId: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await cacheApi.query(queryText, threshold, referenceModelId)
      setQueryResult(result)
      await refreshAll()
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  const addEntry = async (key: string, response: string) => {
    try {
      await cacheApi.addEntry(key, response)
      await refreshAll()
    } catch (e: any) {
      throw new Error(e?.response?.data?.detail || 'Failed to add entry')
    }
  }

  return {
    entries,
    stats,
    history,
    timeline,
    queryResult,
    loading,
    error,
    query,
    addEntry,
  }
}
