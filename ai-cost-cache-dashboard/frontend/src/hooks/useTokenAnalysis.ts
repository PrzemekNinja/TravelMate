import { useState } from 'react'
import { tokensApi } from '../lib/api'
import type { TokenAnalysisResult } from '../lib/types'

export function useTokenAnalysis() {
  const [result, setResult] = useState<TokenAnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const analyze = async (requestText: string, responseText: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await tokensApi.analyze(requestText, responseText)
      setResult(data)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return { result, loading, error, analyze }
}
