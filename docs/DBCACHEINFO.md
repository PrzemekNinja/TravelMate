# Semantic Cache z PostgreSQL + pgvector — Kompletna dokumentacja

> Dokument wyjaśnia jak wykorzystujemy bazę danych PostgreSQL z rozszerzeniem pgvector jako semantyczny cache w architekturze TravelMate AI — czym jest, jak działa, jakie daje korzyści i jak wygląda pod kątem technicznym.

---

## 1. Problem który rozwiązujemy

### 1.1 Bez cache — każde zapytanie kosztuje

W architekturze bez cache, każde zapytanie użytkownika uruchamia pełny pipeline AI:
- 6 agentów LLM
- ~25 000 tokenów
- ~$0.03-0.35 per zapytanie (zależnie od modelu)
- ~15-45 sekund latency

Przy 1000 zapytań/dzień = **$30-350/dzień** na same tokeny LLM.

### 1.2 Obserwacja: zapytania się powtarzają

Analiza zapytań w travel plannerze pokazuje że:
- ~30% zapytań dotyczy tych samych 20 popularnych destynacji (Praga, Rzym, Barcelona, Paryż...)
- ~50% zapytań jest **semantycznie podobnych** do wcześniejszych (np. "3 dni Praga piwo" ≈ "4 dni Praga kultura piwna")
- Wiedza geograficzna (atrakcje, transport, restauracje) zmienia się rzadko (tygodnie/miesiące)

### 1.3 Rozwiązanie: Semantic Cache

Zamiast wywoływać LLM za każdym razem — sprawdź najpierw czy podobne zapytanie było już obsłużone. Jeśli tak — zwróć zapisany wynik. Oszczędzasz tokeny, czas i pieniądze.

---

## 2. Czym jest Semantic Cache?

### 2.1 Cache tradycyjny vs Semantic Cache

| | Tradycyjny cache (exact match) | Semantic cache (similarity) |
|---|---|---|
| Klucz | Dokładny tekst zapytania | Wektor znaczeniowy (embedding) |
| Hit warunek | Tekst identyczny character-by-character | Znaczenie podobne (cosine similarity ≥ próg) |
| "Praga 3 dni" vs "3 dni w Pradze" | MISS (inny tekst) | **HIT** (to samo znaczenie) |
| "Praga piwo" vs "Praha beer" | MISS (inny język) | **HIT** (to samo znaczenie) |
| Elastyczność | Zerowa | Wysoka |
| Implementacja | HashMap/Redis | Baza wektorowa (pgvector) |

### 2.2 Jak działa semantic similarity?

Każde zapytanie jest zamieniane na **wektor liczbowy** (embedding) — 1536 liczb które reprezentują "znaczenie" zdania w przestrzeni wielowymiarowej.

```
"3 dni w Pradze, piwo i historia"  → [0.23, -0.87, 0.41, ... ] (1536 liczb)
"Praga na 3 dni, kultura piwna"   → [0.21, -0.85, 0.44, ... ] (bardzo podobne!)
"5 dni w Tokio, sushi i anime"    → [0.91,  0.12, -0.63, ...] (zupełnie inne)
```

**Cosine similarity** mierzy jak bardzo dwa wektory "patrzą w tym samym kierunku":
- 1.0 = identyczne znaczenie
- 0.85+ = to samo pytanie, inne słowa
- 0.70-0.85 = podobne, ale są różnice
- < 0.50 = zupełnie różne zapytania

---

## 3. Dlaczego PostgreSQL + pgvector?

### 3.1 Alternatywy rozważone

| Technologia | Zalety | Wady | Decyzja |
|---|---|---|---|
| **PostgreSQL + pgvector** | Jedna baza, SQL + wektory, JSONB, transakcje, backup, Azure managed | Wolniejszy niż dedykowane bazy wektorowe przy 1M+ wpisów | ✅ Wybrane |
| Pinecone | Szybki ANN, managed | Osobna baza, vendor lock-in, brak SQL, drogi | ❌ |
| Qdrant | Open source, szybki | Osobna infrastruktura, brak SQL | ❌ |
| Redis + RediSearch | Szybki, w pamięci | Brak persystencji (restart = utrata danych), ograniczone query | ❌ |
| ChromaDB | Prosty, Python-native | Nie skaluje się, brak managed hosting | ❌ |

### 3.2 Dlaczego PostgreSQL wygrywa dla TravelMate

1. **Jedna baza na wszystko** — wektory, dane strukturalne (JSONB), metryki, security events. Nie potrzebujesz 3 osobnych baz.

2. **Filtrowanie PRZED wyszukiwaniem wektorowym** — np. `WHERE destination = 'Prague'` drastycznie zmniejsza zbiór wektorów do przeszukania (100x szybciej).

3. **Transakcje i spójność** — zapis do cache i aktualizacja hit_count w jednej transakcji. Brak ryzyka niespójnych danych.

4. **Azure managed** — Azure Database for PostgreSQL Flexible Server z rozszerzeniem pgvector. Backup, monitoring, skalowanie — bez zarządzania infrastrukturą.

5. **SQL** — zespół zna SQL. Nie trzeba uczyć się nowego query language (jak w Pinecone czy Qdrant).

6. **Skala wystarczająca** — przy 90 000 wpisów (1000 req/dzień × 90 dni TTL) PostgreSQL z HNSW index obsługuje query w < 20ms. Dedykowana baza wektorowa jest potrzebna dopiero przy 10M+ wpisów.

---

## 4. Korzyści biznesowe semantic cache

### 4.1 Redukcja kosztów LLM

| Scenariusz | Koszt/miesiąc | Oszczędność |
|---|---|---|
| Bez cache (1000 req/dzień) | $4 500 | — |
| Z cache 20% hit rate | $3 600 | $900 (20%) |
| Z cache 40% hit rate | $2 700 | $1 800 (40%) |
| Z cache + partial hit 60% | $1 350 | $3 150 (70%) |
| Docelowo (mature cache) | $970 | $3 530 (78%) |

### 4.2 Redukcja latency

| Ścieżka | Latency P95 | Poprawa |
|---|---|---|
| Full Miss (bez cache) | 25-45s | baseline |
| **Full Hit (z cache)** | **< 1s** | **25-45x szybciej** |
| Partial Hit | 8-15s | 2-3x szybciej |

### 4.3 Spójność odpowiedzi

Te same pytania = te same odpowiedzi. Użytkownik nie dostaje losowo lepszych lub gorszych planów zależnie od "nastroju" modelu (temperature, sampling).

### 4.4 Odporność na awarie LLM

Jeśli provider LLM (Google, OpenAI) ma awarię — cached responses nadal działają. System nie jest w 100% zależny od zewnętrznych API.

---

## 5. Architektura techniczna

### 5.1 Schemat bazy danych

```sql
-- Główna tabela cache
CREATE TABLE semantic_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Klucz semantyczny
    query_key       TEXT NOT NULL,              -- oryginalne zapytanie (do wyświetlenia)
    query_embedding VECTOR(1536) NOT NULL,      -- embedding zapytania (do wyszukiwania)
    
    -- Przechowywane odpowiedzi (per agent)
    profile_summary   TEXT,                    -- output profile_agent
    transport_report  TEXT,                    -- output transport_agent
    geo_output        JSONB,                   -- output geo_agent (strukturalny)
    itinerary_draft   JSONB,                   -- output itinerary_agent (strukturalny)
    response_md       TEXT NOT NULL,           -- finalny plan Markdown
    response_html     TEXT,                    -- opcjonalnie wygenerowany HTML
    
    -- Parametry zapytania (do filtrowania i Partial Hit)
    request_params    JSONB NOT NULL,          -- pełny ItineraryInput jako JSON
    destination       TEXT,                    -- wyciągnięte dla szybkiego filtrowania
    days              INTEGER,
    budget            TEXT,
    language          TEXT DEFAULT 'pl',
    
    -- Metadane generacji
    model_used        TEXT,                    -- jaki model wygenerował
    complexity_tier   TEXT,                    -- simple / standard / complex
    total_tokens      INTEGER,                -- ile tokenów kosztowało
    generation_cost   DECIMAL(10,6),           -- koszt w USD
    
    -- Statystyki cache
    hit_count         INTEGER DEFAULT 0,       -- ile razy użyty
    last_hit_at       TIMESTAMPTZ,             -- kiedy ostatnio użyty
    confidence_score  DECIMAL(3,2) DEFAULT 1.0,-- 0.00-1.00 (spada przy failed validation)
    
    -- Lifecycle
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    expires_at        TIMESTAMPTZ,             -- NULL = nie wygasa automatycznie
    is_active         BOOLEAN DEFAULT TRUE,    -- FALSE = wyłączony z wyników
    source            TEXT DEFAULT 'pipeline', -- pipeline / manual / import / seed
    
    -- Audit
    created_by        TEXT,                    -- user_id lub 'system'
    invalidated_by    TEXT,                    -- kto wyłączył
    invalidation_reason TEXT                   -- dlaczego wyłączony
);

-- Indeks wektorowy HNSW — kluczowy dla szybkiego wyszukiwania
-- m=16: liczba połączeń per węzeł (więcej = dokładniej ale wolniej)
-- ef_construction=64: jakość budowania indeksu
CREATE INDEX idx_cache_embedding ON semantic_cache
    USING hnsw (query_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Indeks dla filtrowania przed wyszukiwaniem wektorowym
CREATE INDEX idx_cache_destination ON semantic_cache (destination, is_active);
CREATE INDEX idx_cache_active ON semantic_cache (is_active, created_at DESC);

-- Indeks dla TTL (automatyczne czyszczenie wygasłych)
CREATE INDEX idx_cache_expires ON semantic_cache (expires_at)
    WHERE expires_at IS NOT NULL AND is_active = TRUE;

-- Tabela statystyk (dzienne agregaty)
CREATE TABLE cache_stats (
    id          BIGSERIAL PRIMARY KEY,
    date        DATE NOT NULL UNIQUE,
    total_queries   INTEGER DEFAULT 0,
    full_hits       INTEGER DEFAULT 0,
    partial_hits    INTEGER DEFAULT 0,
    full_misses     INTEGER DEFAULT 0,
    hit_rate_pct    DECIMAL(5,2) DEFAULT 0,
    tokens_saved    BIGINT DEFAULT 0,
    cost_saved_usd  DECIMAL(10,4) DEFAULT 0,
    avg_hit_latency_ms INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 Embedding model

| | Rekomendacja |
|---|---|
| Model | `text-embedding-3-small` (OpenAI) |
| Wymiary | 1536 |
| Koszt | $0.02 / 1M tokenów (~$0.000002 per zapytanie) |
| Latency | ~50ms per embedding |
| Alternatywa | `text-embedding-004` (Google) — podobna jakość |

**Ważne**: zmiana modelu embeddingowego wymaga re-embeddingu CAŁEJ bazy. To jest decyzja długoterminowa — nie zmieniaj modelu bez planu migracji.

### 5.3 Indeks HNSW — jak działa wyszukiwanie

HNSW (Hierarchical Navigable Small World) to algorytm przybliżonego wyszukiwania najbliższych sąsiadów (ANN — Approximate Nearest Neighbors).

**Jak działa (uproszczone):**
1. Buduje wielopoziomowy graf z wektorów
2. Wyszukiwanie zaczyna od "góry" (przybliżone)
3. Schodzi "w dół" do coraz dokładniejszych sąsiadów
4. Zwraca top-N najbliższych wektorów

**Parametry:**
- `m = 16` — ile połączeń ma każdy węzeł (trade-off: pamięć vs dokładność)
- `ef_construction = 64` — jakość budowania indeksu (wyższe = lepsze wyniki ale dłuższy build)

**Wydajność:**
- 10 000 wpisów: query < 5ms
- 100 000 wpisów: query < 20ms
- 1 000 000 wpisów: query < 50ms

---

## 6. Trzy ścieżki cache — szczegółowy flow

### 6.1 Ścieżka A — Full Hit (similarity ≥ 0.88 + parametry identyczne)

```
Zapytanie: "4 dni w Pradze, Mid, piwo i historia"
                    │
                    ▼
         Wygeneruj embedding ($0.000002, ~50ms)
                    │
                    ▼
         PostgreSQL ANN search (~10ms)
         SELECT ... ORDER BY embedding <=> $query LIMIT 5
                    │
                    ▼
         Najlepszy match: similarity = 0.94
         Cached: "4 dni Praga, Mid, piwo i historia"
                    │
                    ▼
         Cache Decision Engine sprawdza:
         ✓ similarity ≥ 0.88
         ✓ destination identyczna
         ✓ days identyczne (4 = 4)
         ✓ budget identyczny (Mid = Mid)
         ✓ interests overlap ≥ 80%
                    │
                    ▼
         Cache Relevance Check (Gemini Flash, ~200ms)
         "Czy ten plan pasuje do nowego zapytania?" → TAK
                    │
                    ▼
         Zwróć response_md z bazy
         Formatter Agent dostosowuje styl (~500ms)
                    │
                    ▼
         UPDATE hit_count = hit_count + 1, last_hit_at = NOW()
                    │
                    ▼
         Odpowiedź do użytkownika

TOTAL: ~800ms | Koszt: ~$0.001 | Tokeny LLM: ~300 (tylko formatter)
```

### 6.2 Ścieżka B — Partial Hit (similarity 0.70–0.87 lub różnica parametrów)

```
Zapytanie: "5 dni w Pradze, Mid, piwo i historia"
                    │
                    ▼
         Najlepszy match: similarity = 0.82
         Cached: "4 dni Praga, Mid, piwo i historia"
         RÓŻNICA: days (4 vs 5)
                    │
                    ▼
         Cache Relevance Check → TAK (destynacja i zainteresowania identyczne)
                    │
                    ▼
         Cache Decomposer analizuje różnice:
         ✅ profile_summary   → REUŻYJ (pace/interests identyczne)
         ✅ transport_report  → REUŻYJ (trasa identyczna)
         ✅ geo_output        → REUŻYJ (destynacja identyczna, HERE data aktualne)
         🔄 itinerary_draft  → GENERUJ OD NOWA (days się różni: 4→5)
         🔄 verification     → GENERUJ OD NOWA (nowy itinerary)
         🔄 formatter        → GENERUJ OD NOWA (zawsze)
                    │
                    ▼
         Uruchom 3 agenty (zamiast 6):
         itinerary_agent: dostaje geo_output z BAZY + profile z BAZY
         verification_agent: weryfikuje nowy plan
         formatter_agent: formatuje
                    │
                    ▼
         verification_agent (Layer 2) sprawdza spójność → OK
                    │
                    ▼
         ZAPISZ nowy wpis do cache (nowe zapytanie + nowy output)
                    │
                    ▼
         Odpowiedź do użytkownika

TOTAL: ~10s | Koszt: ~$0.015 | Tokeny: ~8 000 (3 agenty zamiast 6)
Oszczędność vs Full Miss: ~50-60% tokenów, ~40% czasu
```

### 6.3 Ścieżka C — Full Miss (similarity < 0.70)

```
Zapytanie: "10 dni Japonia + Korea, Luxury, podróż poślubna"
                    │
                    ▼
         Najlepszy match: similarity = 0.35 (nic podobnego w bazie)
                    │
                    ▼
         Cache Decision Engine: FULL MISS
                    │
                    ▼
         Complexity Router → COMPLEX tier
         Query Enricher → dodaje kontekst sezonowy
         profile_agent + transport_agent (równolegle)
         geo_agent → itinerary_agent → verification_agent → formatter_agent
                    │
                    ▼
         ZAPISZ do cache (dla przyszłych podobnych zapytań):
         INSERT INTO semantic_cache (
             query_embedding, query_key, request_params,
             profile_summary, transport_report, geo_output,
             itinerary_draft, response_md, destination,
             model_used, total_tokens, expires_at
         )
                    │
                    ▼
         Odpowiedź do użytkownika

TOTAL: ~35s | Koszt: ~$0.25 | Tokeny: ~25 000 (pełny pipeline)
ALE: następne podobne zapytanie trafi na Ścieżkę A lub B!
```

---

## 7. Strategia TTL (Time To Live) — jak długo dane są aktualne

### 7.1 Tabela TTL per typ wiedzy

| Komponent | TTL | Uzasadnienie | Przykład |
|---|---|---|---|
| Geo clustering (strefy, POI) | 90 dni | Atrakcje zmieniają się rzadko | "Stare Miasto Praga = morning zone" |
| HERE coordinates + adresy | 90 dni | Adresy się nie zmieniają | lat/lng, ulica, numer |
| TripAdvisor ratings | 30 dni | Oceny się zmieniają | Rating 4.5/5 |
| Profile podróżnika | 90 dni | Archetypy są stabilne | "Cultural Explorer, Beer Focus" |
| Transport ogólny | 30 dni | Opcje lotów/PKP się zmieniają | "Lot WAW-PRG, PKP opcja" |
| Transport z konkretnymi datami | 1 dzień | Ceny na datę są zmienne | "10 lipca 2026, lot $120" |
| Itinerary (plan dnia) | 30 dni | Plan może stać się nieaktualny | "Dzień 1: Old Town..." |
| Wiedza ogólna (kultura, kuchnia) | 180 dni | Fakty kulturowe są stabilne | "Czym jest svíčková" |

### 7.2 Automatyczne czyszczenie

Background job co noc:
```sql
-- Usuń wygasłe wpisy
UPDATE semantic_cache 
SET is_active = FALSE
WHERE expires_at < NOW() AND is_active = TRUE;

-- Usuń wpisy z niskim confidence (wielokrotnie failed validation)
UPDATE semantic_cache
SET is_active = FALSE
WHERE confidence_score < 0.3 AND is_active = TRUE;
```

### 7.3 Seed data — rozgrzewanie cache

Przed uruchomieniem produkcji — warto "rozgrzać" cache popularnymi destynacjami:
- 20 najpopularniejszych miast × 3 warianty (3d/5d/7d) × 3 budżety = 180 wpisów
- Wygenerowane offline, zaimportowane jako `source = 'seed'`
- Cache hit rate od pierwszego dnia: ~20-30% zamiast 0%

---

## 8. Cache Validation Gate — ochrona przed fałszywymi hitami

### 8.1 Problem: similarity ≠ poprawność

Score 0.85 oznacza "wektory są blisko" — nie "plan jest poprawny dla tego zapytania".

Przykłady fałszywych hitów:
- "Praga wegetarianie" → cache zwraca "Praga piwo" (sim=0.84, inna dieta!)
- "Barcelona zimą" → cache zwraca "Barcelona latem" (sim=0.81, inny sezon!)
- "Frankfurt am Main" → cache zwraca "Frankfurt an der Oder" (sim=0.95, inne miasto!)

### 8.2 Warstwa 1 — Cache Relevance Check (szybki LLM)

Model: Gemini Flash (~$0.001)
Pytanie: "Czy ten cached plan odpowiada na nowe zapytanie?"
Sprawdza: destynacja, zainteresowania, budżet, sezon, constraints
Akcja: TAK → kontynuuj, NIE → fallback do Full Miss

### 8.3 Warstwa 2 — verification_agent jako quality guard (tylko Partial Hit)

Po złożeniu cache + nowe dane → verification_agent sprawdza:
- Czy plan jest spójny (cache geo + nowy itinerary)?
- Czy wszystkie constraints użytkownika są spełnione?
- Czy daty/sezon się zgadzają?

Akcja: ZGADZA → kontynuuj, NIE ZGADZA → fallback do Full Miss

### 8.4 Samonaprawiający się cache

Każdy failed validation:
1. Obniża `confidence_score` wpisu o 0.2
2. Po 3 failed validations → `is_active = FALSE`
3. Wpis jest logowany do analizy (dlaczego nie pasował?)

Efekt: cache z czasem staje się coraz bardziej precyzyjny — słabe wpisy są eliminowane.

---

## 9. Zapytania SQL — kluczowe operacje

### 9.1 Cache Lookup (wyszukiwanie)

```sql
-- Szukaj 5 najbliższych wpisów dla danej destynacji
SELECT
    id,
    query_key,
    request_params,
    profile_summary,
    transport_report,
    geo_output,
    itinerary_draft,
    response_md,
    1 - (query_embedding <=> $1) AS similarity,
    confidence_score
FROM semantic_cache
WHERE is_active = TRUE
  AND (destination = $2 OR $2 IS NULL)  -- filtruj po destynacji (opcjonalnie)
  AND (expires_at IS NULL OR expires_at > NOW())
  AND confidence_score > 0.5
ORDER BY query_embedding <=> $1  -- sortuj po cosine distance
LIMIT 5;
```

Czas wykonania: < 20ms przy 100K wpisów (dzięki indeksowi HNSW).

### 9.2 Cache Write (zapis nowego wpisu)

```sql
INSERT INTO semantic_cache (
    query_key, query_embedding, request_params,
    profile_summary, transport_report, geo_output, itinerary_draft,
    response_md, destination, days, budget, language,
    model_used, complexity_tier, total_tokens, generation_cost,
    expires_at, source, created_by
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8,
    $9, $10, $11, $12, $13, $14, $15, $16,
    NOW() + INTERVAL '90 days',
    'pipeline',
    $17
);
```

### 9.3 Cache Hit update

```sql
UPDATE semantic_cache
SET hit_count = hit_count + 1,
    last_hit_at = NOW()
WHERE id = $1;
```

### 9.4 Cache invalidation (wyłączenie wpisu)

```sql
UPDATE semantic_cache
SET is_active = FALSE,
    invalidated_by = $2,
    invalidation_reason = $3
WHERE id = $1;
```

### 9.5 Statystyki dzienne

```sql
INSERT INTO cache_stats (date, total_queries, full_hits, partial_hits, full_misses,
                         hit_rate_pct, tokens_saved, cost_saved_usd)
VALUES (
    CURRENT_DATE,
    $1, $2, $3, $4,
    ROUND(($2 + $3)::DECIMAL / GREATEST($1, 1) * 100, 2),
    $5, $6
)
ON CONFLICT (date) DO UPDATE SET
    total_queries = cache_stats.total_queries + EXCLUDED.total_queries,
    full_hits = cache_stats.full_hits + EXCLUDED.full_hits,
    partial_hits = cache_stats.partial_hits + EXCLUDED.partial_hits,
    full_misses = cache_stats.full_misses + EXCLUDED.full_misses,
    tokens_saved = cache_stats.tokens_saved + EXCLUDED.tokens_saved,
    cost_saved_usd = cache_stats.cost_saved_usd + EXCLUDED.cost_saved_usd;
```

---

## 10. Metryki i monitoring cache

### 10.1 Kluczowe metryki

| Metryka | Cel | Alert jeśli |
|---|---|---|
| Hit rate (Full + Partial) | > 40% | < 15% (cache nie działa) |
| Avg hit latency | < 500ms | > 2000ms (problem z bazą) |
| Cache size (wpisy) | Rosnący | Spada (TTL za agresywne) |
| Confidence avg | > 0.8 | < 0.5 (dużo failed validations) |
| Tokens saved/dzień | Rosnący | Spadek (problem z hit rate) |
| Cost saved/miesiąc | > $1000 | < $500 (ROI cache jest niski) |

### 10.2 Dashboard cache

```
┌───────────────────────────────────────────────────┐
│ SEMANTIC CACHE - DASHBOARD                        │
│                                                   │
│ Hit Rate: 42%  │ Entries: 12,340  │ Avg Conf: 0.87│
│                                                   │
│ Today: 1000 queries                               │
│   Full Hit:    350 (35%) │ Cost saved: $4.20      │
│   Partial Hit: 120 (12%) │ Tokens saved: 8.7M    │
│   Full Miss:   530 (53%) │ Avg latency: 420ms    │
│                                                   │
│ Top cached destinations:                          │
│   Prague: 234 hits │ Rome: 189 │ Barcelona: 156   │
└───────────────────────────────────────────────────┘
```

---

## 11. Porównanie z obecnym POC (AI Cost & Cache Dashboard)

Obecny dashboard w `ai-cost-cache-dashboard/` to **demo/showcase** — nie produkcyjny cache:

| | Demo (obecne) | Produkcja (docelowe) |
|---|---|---|
| Storage | In-memory (Python dict) | PostgreSQL + pgvector |
| Embeddings | Keyword overlap (mock) | text-embedding-3-small |
| Persystencja | Brak (restart = utrata) | Pełna (PostgreSQL) |
| Seed data | 25 wpisów statycznych | 180+ seed + rosnący organicznie |
| Walidacja | Brak | 2-warstwowa (Relevance + verification) |
| TTL | Brak | Per typ wiedzy (1-180 dni) |
| Partial Hit | Brak | Cache Decomposer + selective agents |
| Koszt | $0 (brak API) | ~$100-150/mies (PostgreSQL) + ~$2/mies (embeddingi) |
| Skala | 25 wpisów | 90 000+ wpisów |

---

## 12. Dlaczego cache jest warunkiem skalowania (nie opcją)

### Bez cache — koszty rosną liniowo ze skalą:
```
1 000 req/dzień → $2 543/miesiąc (LLM)
5 000 req/dzień → $12 715/miesiąc (LLM)
10 000 req/dzień → $25 430/miesiąc (LLM)
```

### Z cache (40% hit rate) — koszty rosną wolniej:
```
1 000 req/dzień → $970/miesiąc (LLM + cache infra)
5 000 req/dzień → $4 300/miesiąc
10 000 req/dzień → $8 200/miesiąc
```

**Oszczędność przy 10K req/dzień: $17 230/miesiąc ($207K/rok)**

Cache nie jest optymalizacją "nice-to-have" — jest **warunkiem rentowności** przy skali > 2000 req/dzień.

---

*Dokument: DBCACHEINFO.md | Wersja: 1.0 | Data: 2026-06-11*
