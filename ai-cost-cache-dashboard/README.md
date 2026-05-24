# AI Cost & Cache Dashboard

Internal showcase tool for TravelMate — visualizes LLM token costs across models and demonstrates semantic caching.

## Features

**Token Cost Comparison**
- Paste any TravelMate trip request + response
- See exact token counts (input / output / total)
- Compare cost across 8 models: Claude 3.5 Sonnet, Claude Haiku, GPT-4.1, GPT-4o-mini, Gemini 2.5 Flash, Gemini 1.5 Pro, Llama 3, Kimi
- Interactive bar chart + detailed table with savings %

**Semantic Cache Showcase**
- 25 pre-seeded travel knowledge entries (Prague, Rome, Tokyo, Barcelona, Amsterdam)
- Semantic similarity search — similar queries hit the cache even if not identical
- Real-time hit/miss visualization with similarity score
- Cumulative savings chart
- Add your own cache entries

## Quick Start

```bash
cd ai-cost-cache-dashboard
./start.sh
```

Then open **http://localhost:5173**

## Manual Start

**Backend (port 8001):**
```bash
cd backend
cp .env.example .env   # DEMO_MODE=true by default
pip3 install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

**Frontend (port 5173):**
```bash
cd frontend
npm install
npm run dev
```

## Demo Mode vs Live Mode

| | Demo Mode (`DEMO_MODE=true`) | Live Mode (`DEMO_MODE=false`) |
|---|---|---|
| Token counting | ✅ Real (tiktoken) | ✅ Real (tiktoken) |
| Embeddings | Mock (hash-based) | Real (sentence-transformers) |
| API keys needed | ❌ None | ❌ None (local model) |
| First startup | Fast | Slow (downloads ~90MB model) |

## Pricing Data

Prices are in `backend/data/pricing.json`. Update the file anytime — changes take effect on the next analysis run without restarting.

## API Docs

FastAPI auto-docs available at **http://localhost:8001/docs**
