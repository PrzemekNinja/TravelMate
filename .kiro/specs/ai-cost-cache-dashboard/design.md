# Design Document: AI Cost & Cache Dashboard

## Overview

Standalone internal web application built with **FastAPI** (backend) + **React + Vite + Tailwind CSS + shadcn/ui** (frontend). Dark-mode first, modern design. Runs independently from TravelMate but can read TravelMate output files. No Docker required for dev — single `start.sh` script.

---

## Architecture

```
ai-cost-cache-dashboard/
├── backend/                  # FastAPI Python backend
│   ├── main.py               # FastAPI app, CORS, routes
│   ├── routers/
│   │   ├── tokens.py         # Token counting & cost comparison endpoints
│   │   └── cache.py          # Semantic cache endpoints
│   ├── services/
│   │   ├── tokenizer.py      # tiktoken-based token counting
│   │   ├── pricing.py        # Pricing table loader & cost calculator
│   │   └── semantic_cache.py # In-memory vector cache with cosine similarity
│   ├── data/
│   │   ├── pricing.json      # LLM pricing table (updatable without code change)
│   │   └── cache_seed.json   # Pre-seeded travel knowledge entries
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # React + Vite + Tailwind + shadcn/ui
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── TokenCost.tsx     # Token cost comparison page
│   │   │   └── SemanticCache.tsx # Semantic cache showcase page
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.tsx
│   │   │   │   └── DemoBanner.tsx
│   │   │   ├── token/
│   │   │   │   ├── InputPanel.tsx
│   │   │   │   ├── TokenSummary.tsx
│   │   │   │   ├── CostChart.tsx      # Recharts horizontal bar chart
│   │   │   │   └── CostTable.tsx
│   │   │   └── cache/
│   │   │       ├── QueryPanel.tsx
│   │   │       ├── HitMissBadge.tsx
│   │   │       ├── CacheEntryList.tsx
│   │   │       ├── SavingsChart.tsx   # Recharts line chart
│   │   │       └── StatsBar.tsx
│   │   ├── hooks/
│   │   │   ├── useTokenAnalysis.ts
│   │   │   └── useCacheQuery.ts
│   │   └── lib/
│   │       ├── api.ts             # Axios API client
│   │       └── types.ts           # Shared TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── start.sh                  # Single command: starts backend + frontend
└── README.md
```

---

## Backend Design

### Tech Stack
- **FastAPI** + **uvicorn** — already in TravelMate requirements
- **tiktoken** — token counting (cl100k_base)
- **numpy** — cosine similarity for semantic cache
- **sentence-transformers** (optional, fallback to mock embeddings in demo mode)
- **python-dotenv** — config

### API Endpoints

#### Token Cost Module

```
POST /api/tokens/analyze
Body: { "request_text": "...", "response_text": "..." }
Response: {
  "input_tokens": 342,
  "output_tokens": 1850,
  "total_tokens": 2192,
  "costs": [
    {
      "provider": "Anthropic",
      "model": "Claude 3.5 Sonnet",
      "input_cost_usd": 0.001026,
      "output_cost_usd": 0.027750,
      "total_cost_usd": 0.028776,
      "savings_vs_most_expensive_pct": 12.3
    },
    ...
  ],
  "pricing_last_updated": "2025-01-15",
  "pricing_stale": false
}
```

#### Semantic Cache Module

```
GET  /api/cache/entries          # List all cache entries
POST /api/cache/entries          # Add new entry
POST /api/cache/query            # Query cache
Body: { "query": "...", "threshold": 0.85, "reference_model": "gpt-4o-mini" }
Response: {
  "hit": true,
  "similarity": 0.923,
  "matched_entry": { "key": "...", "response": "...", "created_at": "..." },
  "savings_usd": 0.000234,
  "closest_miss": null
}

GET  /api/cache/stats            # Aggregate stats
GET  /api/cache/history          # Last 20 queries
```

### Pricing Table (`pricing.json`)

```json
{
  "last_updated": "2025-06-01",
  "models": [
    {
      "provider": "Anthropic",
      "model": "Claude 3.5 Sonnet",
      "model_id": "claude-3-5-sonnet",
      "input_price_per_million_usd": 3.00,
      "output_price_per_million_usd": 15.00,
      "color": "#D97706"
    },
    {
      "provider": "Anthropic",
      "model": "Claude Haiku",
      "model_id": "claude-haiku",
      "input_price_per_million_usd": 0.25,
      "output_price_per_million_usd": 1.25,
      "color": "#F59E0B"
    },
    {
      "provider": "OpenAI",
      "model": "GPT-4.1",
      "model_id": "gpt-4.1",
      "input_price_per_million_usd": 2.00,
      "output_price_per_million_usd": 8.00,
      "color": "#10B981"
    },
    {
      "provider": "OpenAI",
      "model": "GPT-4o-mini",
      "model_id": "gpt-4o-mini",
      "input_price_per_million_usd": 0.15,
      "output_price_per_million_usd": 0.60,
      "color": "#34D399"
    },
    {
      "provider": "Google",
      "model": "Gemini 2.5 Flash",
      "model_id": "gemini-2.5-flash",
      "input_price_per_million_usd": 0.075,
      "output_price_per_million_usd": 0.30,
      "color": "#3B82F6"
    },
    {
      "provider": "Google",
      "model": "Gemini 1.5 Pro",
      "model_id": "gemini-1.5-pro",
      "input_price_per_million_usd": 1.25,
      "output_price_per_million_usd": 5.00,
      "color": "#60A5FA"
    },
    {
      "provider": "Meta",
      "model": "Llama 3",
      "model_id": "llama-3",
      "input_price_per_million_usd": 0.06,
      "output_price_per_million_usd": 0.06,
      "color": "#8B5CF6"
    },
    {
      "provider": "Moonshot",
      "model": "Kimi",
      "model_id": "kimi",
      "input_price_per_million_usd": 0.12,
      "output_price_per_million_usd": 0.12,
      "color": "#EC4899"
    }
  ]
}
```

### Semantic Cache Service

- **Storage**: In-memory Python dict `{id: CacheEntry}` — no DB needed for POC
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (local, no API key needed) OR mock embeddings in demo mode
- **Similarity**: cosine similarity via numpy
- **Demo mode**: `DEMO_MODE=true` in `.env` → uses pre-computed mock embeddings, no model download

```python
@dataclass
class CacheEntry:
    id: str
    key: str           # natural language query
    response: str      # cached answer
    embedding: list[float]
    created_at: datetime
    hit_count: int = 0
```

---

## Frontend Design

### Tech Stack
- **React 18** + **TypeScript**
- **Vite** — fast dev server
- **Tailwind CSS** — utility-first styling
- **shadcn/ui** — polished component library (dark mode)
- **Recharts** — charts (bar chart for costs, line chart for savings)
- **Axios** — API calls
- **React Router** — SPA navigation

### Visual Theme
- Dark mode by default (`bg-gray-950`, `bg-gray-900` cards)
- Accent: electric blue `#3B82F6` + emerald `#10B981`
- Provider color coding: Anthropic=amber, OpenAI=emerald, Google=blue, Meta=purple, Moonshot=pink
- Smooth animations via Tailwind transitions

### Page: Token Cost Comparison

```
┌─────────────────────────────────────────────────────────┐
│  NAVBAR: TravelMate AI Dashboard  [Token Cost] [Cache]  │
├─────────────────────────────────────────────────────────┤
│  [DEMO MODE BANNER if active]                           │
├──────────────────┬──────────────────────────────────────┤
│  INPUT PANEL     │  RESULTS PANEL                       │
│                  │                                      │
│  Trip Request    │  Token Summary                       │
│  [JSON editor]   │  ┌────────┬────────┬────────┐        │
│                  │  │ Input  │ Output │ Total  │        │
│  Trip Response   │  │  342   │  1850  │  2192  │        │
│  [MD editor]     │  └────────┴────────┴────────┘        │
│                  │                                      │
│  [Run Analysis]  │  Cost Comparison Chart               │
│                  │  (horizontal bar, sorted cheap→exp)  │
│  Pricing updated │                                      │
│  2025-06-01      │  Cost Table (provider/model/costs)   │
└──────────────────┴──────────────────────────────────────┘
```

### Page: Semantic Cache Showcase

```
┌─────────────────────────────────────────────────────────┐
│  NAVBAR                                                 │
├──────────────────┬──────────────────────────────────────┤
│  QUERY PANEL     │  STATS BAR                           │
│                  │  Queries: 12 | Hits: 9 | Rate: 75%  │
│  [Query input]   ├──────────────────────────────────────┤
│  Threshold: 0.85 │  HIT/MISS RESULT                     │
│  [slider]        │  ┌──────────────────────────────┐    │
│  Model: [select] │  │ 🟢 HIT  Similarity: 0.923    │    │
│  [Search Cache]  │  │ Matched: "Prague attractions" │    │
│                  │  │ Savings: $0.000234            │    │
│  CACHE ENTRIES   │  └──────────────────────────────┘    │
│  [browsable list]│                                      │
│  [+ Add Entry]   │  SAVINGS CHART (cumulative line)     │
│                  │                                      │
│                  │  QUERY HISTORY (last 20)             │
└──────────────────┴──────────────────────────────────────┘
```

---

## Demo Mode

When `DEMO_MODE=true` (default if no API keys):
- Token counting uses tiktoken (no API needed — pure local)
- Embeddings use pre-computed mock vectors stored in `cache_seed.json`
- All features work without any external API calls
- Banner displayed: "⚡ Demo Mode — using pre-computed data. Set DEMO_MODE=false for live embeddings."

---

## Data Flow

### Token Analysis Flow
```
User pastes JSON + Markdown
  → POST /api/tokens/analyze
  → tokenizer.py counts tokens (tiktoken, local)
  → pricing.py loads pricing.json, computes costs for all 8 models
  → Returns sorted cost array
  → Frontend renders chart + table
```

### Cache Query Flow
```
User types query
  → POST /api/cache/query
  → semantic_cache.py embeds query (or uses mock in demo mode)
  → Cosine similarity against all stored embeddings
  → Returns hit/miss + similarity score + savings estimate
  → Frontend updates stats, history, savings chart in real time
```

---

## Sample Data

Uses the real Prague 4-day itinerary from TravelMate output as the pre-populated sample response in the Token Cost module. The request JSON uses the TravelMate `ItineraryInput` schema.

Cache seed data covers: Prague, Rome, Tokyo, Barcelona, Amsterdam — city overviews, top attractions, transport, cuisine, seasonal tips (25 entries total).

---

## Startup

```bash
# Install & run (one command)
./start.sh

# Or manually:
cd backend && pip install -r requirements.txt && uvicorn main:app --port 8001 &
cd frontend && npm install && npm run dev
```

Frontend: `http://localhost:5173`
Backend API: `http://localhost:8001`
