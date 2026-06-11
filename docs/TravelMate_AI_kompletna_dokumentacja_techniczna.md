# TravelMate AI — Kompletna Dokumentacja Techniczna

> Architektura, runtime AI, dane, cache, bezpieczeństwo, API, operacje i jakość.
> Wersja: 2.0 | Data: 2026-06-11

---

## Historia wersji

| Wersja | Data | Autor | Zmiany |
|---|---|---|---|
| 1.0 | 2026-05-24 | Zespół TravelMate | Dokument początkowy (docx) |
| 2.0 | 2026-06-11 | Zespół TravelMate | Pełna rozbudowa MD, integracja z ARCHITEKTURA_PRODUKCYJNA, SECURITY, DBCACHEINFO, TOKEN_COUNTING, MAPA_WDROZENIA |

---

## Spis treści

1. Streszczenie techniczne
2. Zakres, założenia i zasady
3. Status POC i architektura docelowa
4. Architektura wysokiego poziomu
5. Komponenty systemu
6. Pipeline AI i agenci
7. Semantic cache, walidacja i Places Graph
8. Model routing i strategia modeli
9. Dane, modele i persystencja
10. API B2C/B2B i przepływy techniczne
11. Bezpieczeństwo, prywatność i zgodność
12. Observability, FinOps i metryki
13. Deployment, środowiska i DevSecOps
14. Testowanie i jakość
15. Operacje, utrzymanie i SLA
16. Uruchomienie lokalne i konfiguracja
17. Roadmapa techniczna
18. Załączniki

---

## 1. Streszczenie techniczne

TravelMate AI jest wieloagentową platformą AI do planowania podróży. System ewoluuje z lokalnego POC opartego o FastAPI, PWA i LangGraph do modularnej platformy produkcyjnej wspierającej B2C, B2B API, semantic cache, dynamiczny routing modeli, guardrails i pełną obserwowalność kosztów.

**Kluczowy wniosek architektoniczny**: LLM nie jest architekturą. Modele językowe są komponentem runtime AI, ale pełna architektura obejmuje przepływ danych, bezpieczeństwo, skalowanie, monitoring, koszty, API, persystencję, integracje zewnętrzne i operacje produkcyjne.

**Stan obecny (POC):**
- FastAPI backend (port 8000) + PWA frontend (Tailwind CSS)
- LangGraph pipeline: 6 agentów (profile, transport, geo, itinerary, verification, formatter)
- Równoległy pipeline: profile + transport działają jednocześnie
- Integracje: HERE Maps, TripAdvisor, multi-provider LLM (Google, Anthropic, OpenAI, LM Studio)
- Token tracking per agent (usage + timing)
- AI Cost & Cache Dashboard (osobna aplikacja analityczna)
- 23 testy jednostkowe
- Zapis artefaktów: HTML (z mapą Leaflet), Markdown, request.json, token_usage.json

**Docelowo (produkcja):**
- Azure (Container Apps + PostgreSQL/pgvector + Redis + API Management)
- Semantic cache z 3 ścieżkami (Full Hit / Partial Hit / Full Miss)
- Dynamiczny routing modeli (3 tiery: Simple/Standard/Complex)
- Security Guards (Input Shield + Output Shield + Prompt Leak Guard)
- B2C freemium + B2B API z webhooks
- Skala: 1000 req/dzień, skalowalne do 10 000+

---

## 2. Zakres, założenia i zasady

### 2.1 Zakres dokumentacji

Dokument opisuje kompletną dokumentację techniczną na poziomie wystarczającym do:
- Prowadzenia prac projektowych
- Rozmów technicznych z inwestorem
- Planowania wdrożenia produkcyjnego
- Przygotowania specyfikacji implementacyjnych

### 2.2 Założenia wejściowe

- Projekt na etapie POC / wczesnego MVP
- Docelowa strategia: AI Travel Commerce Platform (PL + CEE)
- Model biznesowy: B2C-assisted B2B (B2C waliduje wartość, B2B skaluje przychód)
- System model-agnostic (OpenAI, Anthropic, Google, LM Studio)
- transport_agent stały element pipeline'u (wpływa na realność planu i wartość B2B)
- Semantic cache z walidacją = warunek skalowania i rentowności
- Oferty sponsorowane muszą być transparentnie oznaczane

### 2.3 Zasady architektoniczne

1. **Modularność** — każdy komponent wymienialny niezależnie
2. **Model-agnostic** — żaden provider nie jest hardcoded w logice biznesowej
3. **Security by design** — zabezpieczenia od początku, nie jako afterthought
4. **Observability-first** — jeśli nie mierzysz, nie optymalizujesz
5. **Fail gracefully** — każdy komponent ma fallback, nic nie blokuje odpowiedzi
6. **Data minimization** — zbieraj minimum danych, szyfruj, TTL na wszystko
7. **Cost-aware** — każdy request loguje koszt, routing optymalizuje wydatki

---

## 3. Status POC i architektura docelowa

### 3.1 Stan obecny — POC

| Komponent | Status | Szczegóły |
|---|---|---|
| FastAPI backend | ✅ Działa | Port 8000, WebSocket streaming |
| PWA frontend | ✅ Działa | Tailwind, dark/light, My Trips, progress bar |
| LangGraph pipeline | ✅ Działa | 6 agentów, równoległy (profile + transport) |
| HERE Maps | ✅ Działa | Geocoding + POI discover |
| TripAdvisor | ✅ Działa | Zdjęcia, oceny, linki |
| Token tracking | ✅ Działa | Per agent (input/output/elapsed) |
| AI Cost Dashboard | ✅ Działa | 8 modeli, semantic cache demo |
| Auth | ❌ Brak | Do implementacji |
| Rate limiting | ❌ Brak | Do implementacji |
| Semantic cache (produkcyjny) | ❌ Brak | Demo only (in-memory) |
| Security Guards | ❌ Brak | Do implementacji |
| Azure deployment | ❌ Brak | Lokalny serwer |
| B2B API | ❌ Brak | Do implementacji |

### 3.2 Architektura docelowa

Docelowo system obsługuje 1000+ req/dzień z kontrolą kosztów, kolejkowaniem, observability i dojrzałymi procedurami bezpieczeństwa.

Rekomendowany wariant: **Azure-first, modular runtime**:
FastAPI + Container Apps + API Management + PostgreSQL/pgvector + Redis + Blob Storage + LangGraph + Model Gateway + Places Graph + Guardrails + Observability.

Szczegóły: `ARCHITEKTURA_PRODUKCYJNA.md`

---

## 4. Architektura wysokiego poziomu

### 4.1 Warstwy logiczne

```
┌─────────────────────────────────────────────────────────────┐
│ KLIENT: PWA (B2C) │ REST API (B2B) │ WebSocket (admin)     │
├─────────────────────────────────────────────────────────────┤
│ API GATEWAY: Azure API Management (auth, rate limit, WAF)   │
├─────────────────────────────────────────────────────────────┤
│ ORCHESTRATION: FastAPI + LangGraph (Container Apps)         │
├──────────────────────────┬──────────────────────────────────┤
│ AI RUNTIME:              │ DATA LAYER:                      │
│ - Input Shield           │ - PostgreSQL + pgvector (cache)  │
│ - Complexity Router      │ - Redis (sessions, rate limit)   │
│ - Query Enricher         │ - Blob Storage (artefakty)       │
│ - 6 domain agents       │ - Key Vault (sekrety)            │
│ - Output Shield          │                                  │
│ - Prompt Leak Guard      │                                  │
├──────────────────────────┴──────────────────────────────────┤
│ EXTERNAL: OpenAI API │ Anthropic API │ Google API │ HERE │ TA│
├─────────────────────────────────────────────────────────────┤
│ OBSERVABILITY: Azure Monitor + App Insights + Dashboards    │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Komponenty systemu

| Komponent | Technologia | Rola |
|---|---|---|
| Backend API | FastAPI + Uvicorn | Orchestration, routing, WebSocket |
| AI Pipeline | LangGraph (StateGraph) | Multi-agent orchestration |
| Frontend | Vanilla JS + Tailwind + PWA | UI chatowe + My Trips |
| Cache | PostgreSQL 16 + pgvector | Semantic cache + structured data |
| Session store | Redis | Sessions, rate limiting, locks |
| Storage | Azure Blob | HTML/Markdown artefakty |
| Secrets | Azure Key Vault | API keys, connection strings |
| Monitoring | Azure Monitor + App Insights | Logs, metrics, alerts |
| CI/CD | GitHub Actions | Build, test, deploy |
| Embeddings | text-embedding-3-small (OpenAI) | Cache similarity search |
| Tokenization | tiktoken (cl100k_base) | Local token counting |

---

## 6. Pipeline AI i agenci

### 6.1 Pipeline docelowy (z cache i security)

```
User / B2B API
→ Input Shield (regex + LLM classifier)
→ Semantic Cache Lookup (PostgreSQL/pgvector)
→ Cache Relevance Check (Warstwa 1)
→ [Full Hit] → Formatter → Output Shield → Prompt Leak Guard → Response
→ [Partial Hit] → Cache Decomposer → Selective Agents → Verification (Warstwa 2)
→ [Full Miss] → Complexity Router → Query Enricher
    → profile_agent + transport_agent (równolegle)
    → fan_in
    → geo_agent → itinerary_agent → verification_agent
    → Output Shield → Prompt Leak Guard → Formatter
    → Cache Writer + Telemetry
→ Response
```

### 6.2 Agenci POC — szczegóły

| Agent | Input | Output | Model (POC) | Tokeny avg |
|---|---|---|---|---|
| profile_agent | ItineraryInput | profile_summary | Gemini 2.5 Flash | ~1 200 |
| transport_agent | request + profile + baggage | transport_report | Gemini 2.5 Flash | ~1 600 |
| geo_agent | request + profile + HERE context | GeoOutput (strefy + POI) | Gemini 2.5 Flash | ~2 000 |
| itinerary_agent | compact_geo + profile + lodging | ItineraryDraft | Gemini 2.5 Flash | ~4 500 |
| verification_agent | itinerary + geo + request | VerificationOutput | Gemini 2.5 Flash | ~1 700 |
| formatter_agent | ALL outputs (skrócone) | final_markdown | Gemini 2.5 Flash | ~6 500 |

**TOTAL per trip: ~17 500 - 25 000 tokenów (mierzone z API)**

### 6.3 Nowi agenci (produkcja)

| Agent | Rola | Model | Koszt | Kiedy uruchamiany |
|---|---|---|---|---|
| Input Shield | Blokuje injection/jailbreak/PII | Gemini Flash | ~$0.001 | Każdy request |
| Complexity Router | Ocena złożoności, routing modeli | Gemini Flash | ~$0.001 | Cache miss |
| Query Enricher | Kontekst sezonowy/kulturowy, normalizacja | Per tier | ~$0.002 | Cache miss |
| Cache Relevance Check | Walidacja czy cached plan pasuje | Gemini Flash | ~$0.001 | Cache hit/partial |
| Output Shield | Role escape, hallucination check | Gemini Flash | ~$0.001 | Każdy request |
| Prompt Leak Guard | Wykrywanie wycieku promptów | Regex + Flash | ~$0.0005 | Każdy request |

Szczegóły: `ARCHITEKTURA_PRODUKCYJNA.md` sekcje 4-5, `SECURITY.md`

---

## 7. Semantic cache, walidacja i Places Graph

### 7.1 Rola cache w ekonomii systemu

Dane z POC (7 runów, Gemini Flash):
- Średni trip: ~25 000 tokenów = ~$0.05
- Output/input ratio: ~46x (model generuje 46x więcej niż dostaje w request)
- Bez cache przy 1000 req/dzień: ~$1 500-4 500/miesiąc (zależnie od modelu)
- Z cache (40% hit): ~$970/miesiąc

**Semantic cache to warunek rentowności**, nie opcja.

### 7.2 3 ścieżki cache

| Ścieżka | Warunek | Agenci LLM | Koszt | Latency |
|---|---|---|---|---|
| A — Full Hit | similarity ≥ 0.88 + params match | 1 (Formatter) | ~$0.001 | < 1s |
| B — Partial Hit | similarity 0.70-0.87 lub params ≈ | 2-4 (selective) | ~$0.01-0.03 | 5-15s |
| C — Full Miss | similarity < 0.70 | 6-8 (pełny pipeline) | ~$0.02-0.35 | 15-45s |

Docelowy rozkład: A=35%, B=25%, C=40% → efektywna redukcja kosztów ~55-78%

### 7.3 Cache Validation Gate (2 warstwy)

**Problem**: vector similarity ≠ semantyczna poprawność. Score 0.85 nie gwarantuje że plan pasuje.

**Warstwa 1** (Cache Relevance Check): Gemini Flash, ~$0.001, TAK/NIE
**Warstwa 2** (verification_agent): Tylko Path B, sprawdza spójność cache + fresh data

Przy failed validation: confidence_score wpisu spada, po 3x → is_active=FALSE (samonaprawiający się cache).

### 7.4 Places Graph (docelowo)

Baza wiedzy domenowej łącząca:
- Miejsca (POI) z embeddings
- Tagi, źródła, jakość danych
- Opinie, oceny
- Partnerzy, oferty sponsorowane
- Status (aktywne/zamknięte/sezonowe)

Redukuje zależność od LLM dla faktów (adresy, godziny, ceny) + wspiera personalizację.

Szczegóły: `DBCACHEINFO.md`

---

## 8. Model routing i strategia modeli

### 8.1 Zasada: model-agnostic

Dostawca LLM nie może być zakodowany w logice biznesowej. `model_factory.py` z parametrem `model_id` pozwala każdemu agentowi używać innego modelu bez zmiany kodu agenta.

### 8.2 Complexity Router — 3 tiery

| Tier | Score | Modele | Koszt/req | Kiedy |
|---|---|---|---|---|
| SIMPLE | 0-40 | Gemini Flash wszędzie | $0.02-0.05 | Popularne destynacje, krótkie tripy |
| STANDARD | 41-70 | Haiku + Sonnet (itinerary) | $0.05-0.12 | Średnia złożoność |
| COMPLEX | 71-100 | Sonnet + Opus (itinerary) | $0.15-0.35 | Egzotyczne, Luxury, wiele constraints |

Scoring: 6 wymiarów (days, participants, constraints, destination, budget, query quality).

### 8.3 Model Gateway (docelowo)

- Retry z fallback provider (np. Google fail → Anthropic)
- Timeouty per model
- Cost tracking per call
- Prompt versioning i changelog
- A/B testing modeli

Szczegóły: `IMPLEMENTACJA_TECHNICZNA.md` sekcja 2

---

## 9. Dane, modele i persystencja

### 9.1 Domeny danych

| Domena | Storage | Format | TTL |
|---|---|---|---|
| Semantic cache | PostgreSQL + pgvector | VECTOR(1536) + JSONB | 1-180 dni |
| Session data | Redis | JSON | 30 min |
| Artefakty (HTML/MD) | Blob Storage / lokalne output/ | Files | Permanent |
| Security events | PostgreSQL | JSONB | 90 dni |
| Cache stats | PostgreSQL | Tabela | Permanent |
| User data (B2C) | Azure AD B2C | Managed | Account lifetime |
| API keys (B2B) | Azure Key Vault | Encrypted | Until revoked |

### 9.2 Embeddings — zasady wersjonowania

- Model embeddingowy musi być stały przez czas życia cache
- Zmiana modelu = re-embedding całej bazy (migracja)
- Metadane: embedding_model, version, language, created_at
- Przez okres przejściowy: stare i nowe embeddingi równolegle

### 9.3 Token usage data

Każdy run zapisuje `token_usage.json`:
```json
{
  "model_name": "gemini-2.5-flash",
  "provider": "google",
  "total_tokens": 25176,
  "agents": [
    {"agent": "profile_agent", "input_tokens": 1842, "output_tokens": 1523, "elapsed_seconds": 3.21},
    ...
  ]
}
```

Szczegóły: `TOKEN_COUNTING.md`

---

## 10. API B2C/B2B

### 10.1 B2C (obecne endpointy)

| Endpoint | Metoda | Opis |
|---|---|---|
| `/` | GET | PWA frontend |
| `/chat` | POST | Wysłanie zapytania |
| `/admin/logs` | WebSocket | Streaming logów/statusów |
| `/health` | GET | Status (provider, model, active) |
| `/trips` | GET | Lista wygenerowanych planów |
| `/trips/{id}/html` | GET | Serwowanie HTML planu |

### 10.2 B2B API (docelowe)

```http
POST /v1/plans
Authorization: Bearer {api_key}
{
  "destination": "Prague", "days": 4, "budget": "Mid",
  "webhook_url": "https://partner.example.com/webhook",
  "response_format": "json"
}

202 Accepted
{"job_id": "uuid", "status": "queued", "estimated_cost_usd": 0.03}
```

Wymaga: OpenAPI docs, sandbox, API keys, rate limits, usage metering, webhooks, SLA.

---

## 11. Bezpieczeństwo, prywatność i zgodność

### 11.1 5 warstw ochrony

1. Infrastruktura (TLS, WAF, DDoS, VNet)
2. API Gateway (Auth, Rate Limit, Request validation)
3. AI Input (Input Shield — regex + LLM + PII)
4. AI Processing (Sandboxed prompts, instruction hierarchy)
5. AI Output (Output Shield + Prompt Leak Guard)

### 11.2 Prompt Leak Guard

Ostatni bezpiecznik — jedyne zadanie: brak wycieku promptów/kluczy/ścieżek.
- Warstwa 1: Regex (< 1ms, $0)
- Warstwa 2: LLM classifier (~100ms, $0.001)
- Przy wykryciu: BLOKADA + alert + auto-escalation

### 11.3 RODO / AI Act

- PII detection przy zapisie do cache
- Prawo do usunięcia (DELETE /user/data)
- Oznaczanie treści generowanych przez AI
- Transparentne oznaczanie ofert sponsorowanych

Szczegóły: `SECURITY.md`

---

## 12. Observability, FinOps i metryki

### 12.1 Per-request logging

Każdy request loguje:
- trace_id, user_id, request_type (b2c/b2b)
- complexity_tier, cache_path (full_hit/partial/miss)
- agents_run, model_calls (model, tokens, latency, cost)
- security_events, result_status, quality_signals

### 12.2 Dashboardy

1. **Operations** — latency, error rate, throughput
2. **Cost/FinOps** — token usage per tier, cache savings, cost per request
3. **Security** — blocked requests, injection attempts, prompt leaks
4. **Business** — DAU/MAU, popular destinations, conversion, B2B usage

### 12.3 AI Cost & Cache Dashboard (obecny)

Osobna aplikacja (`ai-cost-cache-dashboard/`):
- Token cost comparison (8 modeli LLM)
- Semantic cache showcase (hit/miss visualization)
- Auto-push z TravelMate po każdym runie
- Real pipeline token usage per agent

---

## 13. Deployment, środowiska i DevSecOps

### 13.1 Środowiska

| Środowisko | Przeznaczenie | Dane |
|---|---|---|
| Local | Development | .env, output/ lokalnie |
| Staging | Pre-production testing | Azure, test data |
| Production | Live traffic | Azure, real data |

### 13.2 CI/CD

- Branch protection, PR review, automated tests
- SAST, dependency scanning, secret scanning
- Container build z wersjonowaniem
- Migracje bazy z rollback plan
- Prompt registry z changelog
- Evals regresyjne po zmianie promptów/modeli

---

## 14. Testowanie i jakość

### 14.1 Obecne testy (POC)

23 testy jednostkowe: formatter, input_parser, itinerary, llm_content, markdown_contract, markdown_formatter, output_writer, transport.

```bash
python3 -m pytest tests/ -v  # wszystkie muszą być zielone
```

### 14.2 Docelowe warstwy testów

| Warstwa | Co testuje | Narzędzia |
|---|---|---|
| Unit | Logika agentów, parser, formatter | pytest |
| Integration | Pipeline end-to-end | pytest + mocked LLM |
| Security | Prompt injection bank (50+ cases) | Custom test suite |
| Performance | Latency, throughput | k6, locust |
| Quality | Ocena planów (rubryka jakości) | LLM-as-judge + human review |

---

## 15. Operacje, utrzymanie i SLA

### 15.1 Graceful degradation

| Awaria | Fallback |
|---|---|
| LLM provider down | Fallback do innego providera lub cached responses |
| HERE/TripAdvisor down | geo_agent zwraca unresolved, pipeline kontynuuje |
| Cache validation fail | Full Miss bez ponownego cache lookup |
| Prompt Leak Guard trigger | Blokada + generyczny komunikat |
| Kolejka przeciążona | HTTP 202 + estymacja czasu |

### 15.2 SLA (docelowe B2B)

- Uptime: 99.9%
- Latency P95: < 45s (cache miss), < 1s (cache hit)
- Error rate: < 1%
- Support response time: < 4h (critical), < 24h (normal)

---

## 16. Uruchomienie lokalne i konfiguracja

### 16.1 Wymagania

- Python 3.11+
- Node.js 18+ (dla dashboard)
- Klucz API jednego LLM providera (minimum)

### 16.2 Setup

```bash
git clone https://github.com/PrzemekNinja/TravelMate
cd TravelMate
cp .env.example .env  # uzupełnij klucze
pip install -r requirements.txt -e .
```

### 16.3 Uruchomienie

```bash
# TravelMate (port 8000)
python3 -m travelmate.api.main

# AI Cost Dashboard (porty 8001 + 5173)
cd ai-cost-cache-dashboard && ./start.sh  # Mac/Linux
cd ai-cost-cache-dashboard && start.bat   # Windows
```

### 16.4 Konfiguracja .env

Szablon: `.env.example` w repo. Minimum:
```
MODEL_PROVIDER=google
GOOGLE_API_KEY=your_key_here
GOOGLE_MODEL=gemini-2.5-flash
```

---

## 17. Roadmapa techniczna

| Faza | Tygodnie | Zakres | Deliverable |
|---|---|---|---|
| 1 — Fundament | 1-6 | Azure + PostgreSQL + monitoring | System na chmurze, cache zbiera dane |
| 2 — Cache + Routing | 7-12 | Semantic cache aktywny + Complexity Router | Koszty -30%, cache hit >15% |
| 3 — Security | 13-15 | Input/Output Shield + API Management | Gotowość na ruch publiczny |
| 4 — Launch | 16-18 | B2C freemium + B2B API + hardening | 100 users B2C, 2 klientów B2B |

Szczegóły: `MAPA_WDROZENIA.md`

TCO rok 1: $70K-98K | Break-even: miesiąc 8-10 | ROI rok 2: 129-611%

---

## 18. Załączniki

### 18.1 Powiązane dokumenty

| Dokument | Zawartość |
|---|---|
| `ARCHITEKTURA_PRODUKCYJNA.md` | Pełna architektura z diagramami, 3 ścieżki cache, walidacja |
| `IMPLEMENTACJA_TECHNICZNA.md` | Blueprint implementacji: routing, cache, security, enricher |
| `MAPA_WDROZENIA.md` | Harmonogram 18 tygodni, zasoby, budżet, TCO, ROI |
| `SECURITY.md` | 5 warstw bezpieczeństwa, ataki AI, GDPR, checklist |
| `DBCACHEINFO.md` | PostgreSQL + pgvector, schemat SQL, TTL, metryki |
| `TOKEN_COUNTING.md` | Czym są tokeny, mechanizm zliczania, optymalizacja |
| `ARCHITEKTURA.md` | Opis obecnego POC (agents, graph, tools) |
| `DOKUMENTACJA_TECHNICZNA.md` | Szczegóły techniczne POC |
| `DOKUMENTACJA_BIZNESOWA.md` | Cele biznesowe, KPI, roadmapa produktowa |
| `UZYCIE.md` | Instrukcja uruchomienia i konfiguracji |
| `ROZWOJ.md` | Jak dodawać agentów, testowanie, praktyki |

### 18.2 Definition of Production Ready

- [ ] Auth (JWT + API Key) aktywny
- [ ] Rate limiting aktywny
- [ ] Semantic cache z walidacją (3 ścieżki)
- [ ] Security Guards (Input + Output + Prompt Leak Guard)
- [ ] Każdy plan ma trace ID, koszt, latency, cache path
- [ ] Artefakty w Blob Storage (nie lokalnie)
- [ ] Backup i restore przetestowane
- [ ] B2B API z dokumentacją, sandbox, keys
- [ ] UI oznacza AI, ostrzeżenia, oferty sponsorowane
- [ ] Testy: injection, leak, E2E, load, pentest

### 18.3 Przykładowy ItineraryInput

```json
{
  "destination": "Rzym",
  "days": 3,
  "budget": "Mid",
  "pace": "Moderate",
  "home_location": "Kraków",
  "travel_start_date": "2026-07-10",
  "travel_end_date": "2026-07-13",
  "participants": 2,
  "baggage": [{"owner": "osoba_1", "pieces": 1, "height_cm": 55, "width_cm": 40, "depth_cm": 20, "weight_kg": 8}],
  "interests": ["historia", "sztuka", "street-food"],
  "constraints": ["wegetariańskie opcje"],
  "accommodation_area": "Trastevere"
}
```

---

*Dokument: TravelMate_AI_kompletna_dokumentacja_techniczna.md | Wersja: 2.0 | Data: 2026-06-11*
