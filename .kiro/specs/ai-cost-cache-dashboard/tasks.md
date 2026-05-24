# Implementation Tasks

## Task 1: Project scaffold & backend foundation
- [ ] 1.1 Create `ai-cost-cache-dashboard/backend/` directory structure
- [ ] 1.2 Create `backend/requirements.txt` with fastapi, uvicorn, tiktoken, numpy, python-dotenv, sentence-transformers
- [ ] 1.3 Create `backend/.env.example` with DEMO_MODE, PORT variables
- [ ] 1.4 Create `backend/main.py` — FastAPI app with CORS, health endpoint, demo mode flag
- [ ] 1.5 Create `backend/data/pricing.json` — all 8 models with prices and colors
- [ ] 1.6 Create `backend/data/cache_seed.json` — 25 pre-seeded travel knowledge entries (Prague, Rome, Tokyo, Barcelona, Amsterdam)

## Task 2: Backend token & pricing service
- [ ] 2.1 Create `backend/services/tokenizer.py` — tiktoken cl100k_base token counting
- [ ] 2.2 Create `backend/services/pricing.py` — load pricing.json, compute costs for all models, detect stale pricing
- [ ] 2.3 Create `backend/routers/tokens.py` — POST /api/tokens/analyze endpoint
- [ ] 2.4 Wire tokens router into main.py

## Task 3: Backend semantic cache service
- [ ] 3.1 Create `backend/services/semantic_cache.py` — CacheEntry dataclass, in-memory store, cosine similarity
- [ ] 3.2 Add demo mode: pre-computed mock embeddings loaded from cache_seed.json
- [ ] 3.3 Add live mode: sentence-transformers all-MiniLM-L6-v2 embeddings
- [ ] 3.4 Create `backend/routers/cache.py` — GET /entries, POST /entries, POST /query, GET /stats, GET /history
- [ ] 3.5 Wire cache router into main.py, seed cache on startup

## Task 4: Frontend scaffold
- [ ] 4.1 Create `ai-cost-cache-dashboard/frontend/` with Vite + React + TypeScript template
- [ ] 4.2 Install and configure Tailwind CSS + shadcn/ui (dark mode)
- [ ] 4.3 Install Recharts, Axios, React Router
- [ ] 4.4 Create `src/lib/types.ts` — all TypeScript interfaces (TokenAnalysis, CostEntry, CacheEntry, QueryResult, etc.)
- [ ] 4.5 Create `src/lib/api.ts` — Axios client with base URL, typed request/response functions
- [ ] 4.6 Create `src/App.tsx` — React Router setup with two routes

## Task 5: Layout components
- [ ] 5.1 Create `src/components/layout/Navbar.tsx` — dark navbar with logo, nav links, active state
- [ ] 5.2 Create `src/components/layout/DemoBanner.tsx` — yellow banner shown when DEMO_MODE active

## Task 6: Token Cost page
- [ ] 6.1 Create `src/components/token/InputPanel.tsx` — JSON editor + Markdown editor with pre-populated Prague sample data, Run Analysis button
- [ ] 6.2 Create `src/components/token/TokenSummary.tsx` — 3 stat cards: input/output/total tokens
- [ ] 6.3 Create `src/components/token/CostChart.tsx` — Recharts horizontal bar chart, sorted cheap→expensive, provider color coding, tooltips, cheapest/most expensive highlights
- [ ] 6.4 Create `src/components/token/CostTable.tsx` — full data table with savings % column, provider badges
- [ ] 6.5 Create `src/hooks/useTokenAnalysis.ts` — state management, API call, loading/error states
- [ ] 6.6 Create `src/pages/TokenCost.tsx` — assemble all token components, pricing date display, stale warning

## Task 7: Semantic Cache page
- [ ] 7.1 Create `src/components/cache/StatsBar.tsx` — total queries, hits, misses, hit rate % with animated counters
- [ ] 7.2 Create `src/components/cache/QueryPanel.tsx` — query input, threshold slider (0.5–1.0), model selector dropdown, Search button
- [ ] 7.3 Create `src/components/cache/HitMissBadge.tsx` — green HIT / red MISS result card with similarity score, matched entry preview, savings amount
- [ ] 7.4 Create `src/components/cache/CacheEntryList.tsx` — browsable list of all cache entries with add-entry form
- [ ] 7.5 Create `src/components/cache/SavingsChart.tsx` — Recharts line chart of cumulative savings over session
- [ ] 7.6 Create `src/hooks/useCacheQuery.ts` — state management, query history, cumulative savings tracking
- [ ] 7.7 Create `src/pages/SemanticCache.tsx` — assemble all cache components

## Task 8: Startup scripts & docs
- [ ] 8.1 Create `ai-cost-cache-dashboard/start.sh` — starts backend (port 8001) and frontend (port 5173) concurrently
- [ ] 8.2 Create `ai-cost-cache-dashboard/README.md` — setup instructions, feature overview, screenshots description
- [ ] 8.3 Create `ai-cost-cache-dashboard/.env.example` — top-level env example
