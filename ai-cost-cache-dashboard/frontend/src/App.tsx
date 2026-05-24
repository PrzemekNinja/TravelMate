import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Navbar } from './components/layout/Navbar'
import { DemoBanner } from './components/layout/DemoBanner'
import { TokenCost } from './pages/TokenCost'
import { SemanticCache } from './pages/SemanticCache'
import { healthApi } from './lib/api'

function App() {
  const [demoMode, setDemoMode] = useState(true)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  useEffect(() => {
    healthApi.check()
      .then(data => {
        setDemoMode(data.demo_mode)
        setBackendOk(true)
      })
      .catch(() => setBackendOk(false))
  }, [])

  if (backendOk === false) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-8 text-center max-w-md">
          <h2 className="text-lg font-semibold text-red-400 mb-2">Backend unavailable</h2>
          <p className="text-sm text-gray-400 mb-4">
            Make sure the backend is running on port 8001.
          </p>
          <code className="block rounded bg-gray-900 px-3 py-2 text-xs text-gray-300 mb-4">
            cd ai-cost-cache-dashboard/backend<br />
            uvicorn main:app --port 8001 --reload
          </code>
          <button
            onClick={() => window.location.reload()}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950">
        <Navbar demoMode={demoMode} />
        {demoMode && <DemoBanner />}
        <main>
          <Routes>
            <Route path="/" element={<TokenCost />} />
            <Route path="/cache" element={<SemanticCache />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
