import { useState } from 'react'
import { Play, RotateCcw, AlertCircle } from 'lucide-react'
import { RunPicker } from './RunPicker'
import type { TravelMateRun } from '../../lib/types'

const SAMPLE_REQUEST = JSON.stringify({
  destination: "Prague",
  days: 4,
  budget: "Mid",
  pace: "Relaxed",
  home_location: "Warsaw",
  travel_start_date: "2026-07-10",
  travel_end_date: "2026-07-14",
  participants: 1,
  interests: ["beer culture", "history", "local cuisine", "architecture"],
  constraints: [],
  accommodation_area: "Old Town"
}, null, 2)

const SAMPLE_RESPONSE = `## 🗺️ Prague - Travel Plan (4 Days)

### Day 1: Old Town Charm & Jewish Quarter
**09:00 – 12:00 | Old Town Square & Astronomical Clock**
Immerse yourself in the heart of Prague's history and witness the iconic Astronomical Clock show.

**12:30 | Lunch: U Medvidku**
A historic brewery and restaurant, perfect for experiencing local cuisine and trying their strong X-Beer 33.

**14:00 – 17:00 | Jewish Museum Prague**
Delve into the poignant history of the Jewish Quarter (Josefov).

**19:00 | Dinner: Lokál Dlouhááá**
Bustling, modern take on a traditional Czech pub, popular with locals and tourists.

### Day 2: Castle Views & Lesser Town Taverns
**09:30 – 13:00 | Prague Castle**
Discover one of the largest ancient castle complexes in the world.

**13:30 | Lunch: U Tří jelínků**
A cozy, traditional restaurant in the heart of Lesser Town.

**15:00 – 17:30 | Charles Bridge & Lesser Town**
Walk across the famous Charles Bridge, admiring the baroque statues.

**19:30 | Dinner: U Hrocha**
Authentic, bustling, very local pub experience.

### Day 3: Modern Prague & Vinohrady
**10:00 – 12:30 | Wenceslas Square**
Experience the vibrant commercial and cultural heart of New Town.

**13:00 | Lunch: Restaurace U Pinkasů**
One of Prague's oldest pubs, famous for being the first place to serve Pilsner Urquell.

**19:30 | Dinner: U Sadu**
Authentic, lively, unpretentious local pub.

### Day 4: Brewery Experience & Riverside
**10:00 – 12:30 | Staropramen Brewery Tour**
Delve into the history of one of Prague's oldest breweries.

**14:30 – 17:00 | Museum Kampa & Kampa Island**
Visit Museum Kampa and enjoy a leisurely walk around the island.

**19:30 | Dinner: Kolkovna Celnice**
Lively, traditional, with a slightly more upscale pub feel.

### 💡 Summary
- Mobility: Public transport + walking
- Estimated ticket costs: 1600-2000 CZK per person`

interface InputPanelProps {
  onAnalyze: (request: string, response: string) => void
  onRunSelected?: (runId: string) => void
  loading: boolean
  error: string | null
}

export function InputPanel({ onAnalyze, onRunSelected, loading, error }: InputPanelProps) {
  const [requestText, setRequestText] = useState(SAMPLE_REQUEST)
  const [responseText, setResponseText] = useState(SAMPLE_RESPONSE)
  const [jsonError, setJsonError] = useState<string | null>(null)

  const validateAndRun = () => {
    try {
      JSON.parse(requestText)
      setJsonError(null)
      onAnalyze(requestText, responseText)
    } catch (e) {
      setJsonError('Invalid JSON in Trip Request field')
    }
  }

  const reset = () => {
    setRequestText(SAMPLE_REQUEST)
    setResponseText(SAMPLE_RESPONSE)
    setJsonError(null)
  }

  const loadRun = (run: TravelMateRun) => {
    setRequestText(run.request_json)
    setResponseText(run.itinerary_md)
    setJsonError(null)
    onRunSelected?.(run.id)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Input</h2>
        <button
          onClick={reset}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          <RotateCcw className="h-3 w-3" />
          Reset to sample
        </button>
      </div>

      {/* TravelMate run picker */}
      <RunPicker onSelect={loadRun} />

      {/* Trip Request */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1.5">
          Trip Request <span className="text-gray-600">(JSON)</span>
        </label>
        <textarea
          value={requestText}
          onChange={e => setRequestText(e.target.value)}
          className={`code-editor w-full rounded-lg border bg-gray-900 px-3 py-2.5 text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 ${
            jsonError ? 'border-red-500/50' : 'border-gray-700'
          }`}
          rows={12}
          spellCheck={false}
        />
        {jsonError && (
          <p className="mt-1 flex items-center gap-1 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {jsonError}
          </p>
        )}
      </div>

      {/* Trip Response */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1.5">
          Trip Response <span className="text-gray-600">(Markdown itinerary)</span>
        </label>
        <textarea
          value={responseText}
          onChange={e => setResponseText(e.target.value)}
          className="code-editor w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2.5 text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          rows={12}
          spellCheck={false}
        />
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
          {error}
        </div>
      )}

      <button
        onClick={validateAndRun}
        disabled={loading}
        className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            Analyzing...
          </>
        ) : (
          <>
            <Play className="h-4 w-4" />
            Run Analysis
          </>
        )}
      </button>
    </div>
  )
}
