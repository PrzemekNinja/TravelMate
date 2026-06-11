# Token Counting — Kompletna dokumentacja

> Dokument wyjaśnia czym są tokeny, dlaczego je liczymy, jak działa mechanizm zliczania w TravelMate i jakie ma to znaczenie biznesowe.

---

## 1. Czym jest token?

Token to **najmniejsza jednostka tekstu** którą model AI przetwarza. To nie jest słowo i nie jest litera — to jest coś pomiędzy.

Modele LLM nie czytają tekstu jak ludzie. Rozbijają tekst na kawałki (tokeny) za pomocą algorytmu tokenizacji BPE (Byte Pair Encoding).

### Przykłady tokenizacji

```
"Hello world"         → ["Hello", " world"]          = 2 tokeny
"Tokenization"        → ["Token", "ization"]          = 2 tokeny
"TravelMate AI"       → ["Travel", "Mate", " AI"]    = 3 tokeny
"Kraków"              → ["Kr", "ak", "ów"]           = 3 tokeny
"wegetariańskie"      → ["weget", "arian", "skie"]   = 3 tokeny
```

### Reguły kciuka

- Angielski: ~1 token = ~4 znaki = ~0.75 słowa
- Polski: ~1 token = ~3 znaki (dłuższe słowa, diakrytyki)
- 100 tokenów ≈ 75 słów angielskich ≈ 50-60 słów polskich
- 1000 tokenów ≈ 750 słów ≈ jedna strona A4

---

## 2. Tokeny jako waluta AI

Providery LLM rozliczają się za tokeny, nie za zapytania. Każde wywołanie API ma koszt:

```
Koszt = (input_tokens × cena_input) + (output_tokens × cena_output)
```

### Ceny za 1 milion tokenów (maj 2026)

| Model | Provider | Input $/M | Output $/M | Uwagi |
|---|---|---|---|---|
| Gemini 2.5 Flash | Google | $0.30 | $2.50 | Aktywny w TravelMate POC |
| GPT-4o-mini | OpenAI | $0.15 | $0.60 | Najtańszy OpenAI |
| Claude Haiku 4.5 | Anthropic | $1.00 | $5.00 | Szybki, średnia jakość |
| GPT-4.1 | OpenAI | $2.00 | $8.00 | Dobra jakość/cena |
| Claude Sonnet 4.6 | Anthropic | $3.00 | $15.00 | Wysoka jakość |
| Gemini 2.5 Pro | Google | $1.25 | $10.00 | Google flagship |
| Claude Opus 4.6 | Anthropic | $5.00 | $25.00 | Najwyższa jakość |

### Kluczowe obserwacje

- **Output jest 3-15x droższy niż input** — model "myśli" generując każdy token
- **Różnica między najtańszym a najdroższym modelem to ~170x** (Flash $0.30 vs Opus $25)
- **Jeden trip w TravelMate** to ~25 000 tokenów — koszt $0.03 (Flash) do $1.50 (Opus)

---

## 3. Input vs Output tokeny

### Input tokeny (prompt tokens) — co wysyłasz do modelu

- System prompt (instrukcje dla agenta): ~200 tokenów
- Dane użytkownika (request JSON): ~100 tokenów
- Kontekst z poprzednich agentów: 200-2000 tokenów
- Task prompt (format outputu): ~200 tokenów

### Output tokeny (completion tokens) — co model generuje

- Odpowiedź (plan podróży, profil, raport transportowy)
- Każdy następny token jest generowany sekwencyjnie

### Dlaczego output jest droższy?

Generowanie każdego tokenu outputu wymaga "przejścia" przez cały model (miliardów parametrów) — raz per token. Input jest przetwarzany "hurtem" (parallel processing), output jest sekwencyjny (autoregressive).

Analogia: czytanie książki (input, szybkie) vs pisanie książki (output, wolne i drogie).

---

## 4. Jak działa mechanizm zliczania w TravelMate

### 4.1 Gdzie powstają tokeny w pipeline?

```
profile_agent:      
  Input:  system_prompt + task_prompt + request_json        = ~400 tok
  Output: profil podróżnika                                 = ~800 tok
  Subtotal: ~1 200 tokenów

transport_agent:    
  Input:  system_prompt + task_prompt + request + profile    = ~600 tok
  Output: raport transportowy                                = ~1 000 tok
  Subtotal: ~1 600 tokenów

geo_agent:          
  Input:  system_prompt + task_prompt + request + profile + HERE = ~800 tok
  Output: geo plan (strefy per dzień)                        = ~1 200 tok
  Subtotal: ~2 000 tokenów

itinerary_agent:    ← NAJDROŻSZY AGENT
  Input:  system_prompt + task_prompt + compact_geo + profile = ~1 500 tok
  Output: szczegółowy plan z posiłkami i noclegami           = ~3 000 tok
  Subtotal: ~4 500 tokenów

verification_agent: 
  Input:  system_prompt + task_prompt + itinerary + geo      = ~1 200 tok
  Output: ostrzeżenia i korekty                              = ~500 tok
  Subtotal: ~1 700 tokenów

formatter_agent:    
  Input:  system_prompt + ALL skrócone outputy + baseline    = ~2 500 tok
  Output: finalny plan Markdown                              = ~4 000 tok
  Subtotal: ~6 500 tokenów

═══════════════════════════════════════════════════════════════
TOTAL:  ~12 000 input + ~10 500 output = ~22 500 tokenów
═══════════════════════════════════════════════════════════════
```

### 4.2 Dwa sposoby liczenia w dashboardzie

#### Sposób 1 — tiktoken (lokalne, przybliżone)

Dashboard bierze `request.json` i `itinerary.md` i liczy tokeny lokalnie przez bibliotekę tiktoken (encoding cl100k_base, kompatybilne z GPT-4):

```
Input:  request.json        = 104 tokeny
Output: itinerary.md        = 3 447 tokenów
Total:  3 551 tokenów
```

**To jest niepełny obraz** — widzi tylko wejście użytkownika i końcowy wynik formattera. Nie widzi 5 pośrednich wywołań LLM.

**Kiedy jest użyteczne:** porównywanie kosztów między modelami dla tego samego tekstu (ile by kosztował ten sam output na różnych modelach).

#### Sposób 2 — Real Pipeline Token Usage (z API providerów)

Token tracker w TravelMate przechwytuje `usage_metadata` z odpowiedzi każdego agenta:

```
Total Input:  12 189 tokenów (suma 6 agentów)
Total Output: 12 987 tokenów (suma 6 agentów)
Grand Total:  25 176 tokenów
```

**To jest prawdziwy koszt** — suma wszystkich wywołań LLM w pipeline.

#### Porównanie

| | tiktoken | Real Pipeline |
|---|---|---|
| Co mierzy | request + finalny output | WSZYSTKIE wywołania LLM |
| Wartość | 3 551 tokenów | 25 176 tokenów |
| Mnożnik | 1x | **~7x więcej** |
| Wymaga API | Nie (lokalne) | Tak (z odpowiedzi LLM) |
| Dokładność | Przybliżona | Dokładna |
| Zastosowanie | Porównanie modeli | Prawdziwy koszt |

### 4.3 Implementacja techniczna — token_tracker.py

Token tracker to thread-safe singleton (`travelmate/tools/token_tracker.py`).

**Przepływ:**

```
1. planner_service.py resetuje tracker przed każdym runem
2. planner_service.py ustawia model info (provider, model_name)
3. Każdy agent po llm.invoke():
   - Mierzy czas: _t0 = time.perf_counter()
   - Wywołuje LLM: response = llm.invoke([messages])
   - Mierzy czas: _t1 = time.perf_counter()
   - Raportuje: get_tracker().record("agent_name", response, elapsed=_t1-_t0)
4. planner_service.py zbiera summary po zakończeniu pipeline
5. Zapisuje token_usage.json do output/{run_id}/
6. Push do AI Cost & Cache Dashboard (async)
```

**Wyciąganie tokenów z response (4 formaty):**

```
Format 1 — LangChain standard:
  response.usage_metadata = {"input_tokens": 1842, "output_tokens": 1523}

Format 2 — OpenAI raw:
  response.response_metadata.token_usage = {"prompt_tokens": 1842, "completion_tokens": 1523}

Format 3 — Anthropic raw:
  response.response_metadata.usage = {"input_tokens": 1842, "output_tokens": 1523}

Format 4 — Gemini raw:
  response.response_metadata.usageMetadata = {"promptTokenCount": 1842, "candidatesTokenCount": 1523}
```

Tracker próbuje każdy format po kolei — działa z OpenAI, Anthropic i Google bez żadnej konfiguracji.

### 4.4 Format token_usage.json

```json
{
  "model_name": "gemini-2.5-flash",
  "provider": "google",
  "total_input_tokens": 12189,
  "total_output_tokens": 12987,
  "total_tokens": 25176,
  "agents": [
    {
      "agent": "profile_agent",
      "input_tokens": 1842,
      "output_tokens": 1523,
      "total_tokens": 3365,
      "elapsed_seconds": 3.21
    },
    {
      "agent": "transport_agent",
      "input_tokens": 2105,
      "output_tokens": 2341,
      "total_tokens": 4446,
      "elapsed_seconds": 4.87
    },
    {
      "agent": "geo_agent",
      "input_tokens": 2340,
      "output_tokens": 2102,
      "total_tokens": 4442,
      "elapsed_seconds": 6.12
    },
    {
      "agent": "itinerary_agent",
      "input_tokens": 3012,
      "output_tokens": 3890,
      "total_tokens": 6902,
      "elapsed_seconds": 11.34
    },
    {
      "agent": "verification_agent",
      "input_tokens": 1456,
      "output_tokens": 891,
      "total_tokens": 2347,
      "elapsed_seconds": 3.45
    },
    {
      "agent": "formatter_agent",
      "input_tokens": 1434,
      "output_tokens": 2240,
      "total_tokens": 3674,
      "elapsed_seconds": 5.67
    }
  ]
}
```

---

## 5. Dlaczego zliczanie tokenów jest krytyczne biznesowo

### 5.1 Kontrola kosztów

Przy 1000 zapytań/dzień:

| Strategia | Koszt/dzień | Koszt/miesiąc |
|---|---|---|
| Bez kontroli (Claude Sonnet wszędzie) | $150 | $4 500 |
| Z routingiem modeli (Simple/Standard/Complex) | $54 | $1 622 |
| Z semantic cache (40% hit) + routing | $32 | $970 |

**Oszczędność z token tracking + routing + cache: $3 530/miesiąc (78%)**

### 5.2 Identyfikacja drogich agentów

Token tracker pokazuje rozkład per agent:
- `itinerary_agent`: ~35% całego kosztu
- `formatter_agent`: ~25%
- Reszta: ~40%

Wiedząc to, optymalizujesz celowo:
- Krótszy prompt w itinerary_agent
- Kompresja kontekstu (JSON bez whitespace)
- Cache geo_output (stabilny, zmienia się rzadko)

### 5.3 Rozliczenie B2B

Klienci B2B płacą per zapytanie. Musisz wiedzieć ile kosztuje Ciebie obsługa:
- Simple trip: $0.03 → sprzedajesz za $0.05 (marża 40%)
- Complex trip: $0.25 → sprzedajesz za $0.50 (marża 50%)

Bez token trackingu nie wiesz czy zarabiasz czy tracisz na każdym requeście.

### 5.4 Monitoring anomalii

Nagły wzrost tokenów per agent sygnalizuje problemy:
- **3x więcej niż zwykle** → prompt injection (model generuje niechciane content)
- **10x więcej inputu** → bug w kontekście (za dużo danych do promptu)
- **0 tokenów** → API provider nie zwraca usage_metadata (znany bug Gemini)

### 5.5 A/B testing modeli

Dashboard pokazuje: "ten sam trip kosztuje $0.03 na Gemini Flash vs $0.25 na Claude Sonnet". Można porównać jakość i zdecydować: czy Sonnet jest 8x lepszy żeby uzasadnić 8x wyższą cenę?

---

## 6. Context window — ukryty limit

Każdy model ma limit tokenów które może przetworzyć na raz (input + output łącznie):

| Model | Context window | Praktyczny limit |
|---|---|---|
| Gemini 2.5 Flash | 1 000 000 tok | Praktycznie nieograniczony |
| GPT-4.1 | 1 000 000 tok | Praktycznie nieograniczony |
| Claude Sonnet 4.6 | 200 000 tok | Wystarczający |
| GPT-4o-mini | 128 000 tok | Trzeba uważać przy dużych kontekstach |

Jeśli input + output przekroczy limit → model zwraca błąd. TravelMate obsługuje to:
- `itinerary_agent` łapie `BadRequestError("Context size exceeded")`
- Przechodzi na fallback (plan z geo_output bez LLM)
- `verification_agent` podobnie — zwraca generyczne ostrzeżenie

---

## 7. Optymalizacja tokenów — techniki stosowane w TravelMate

### 7.1 Kompresja JSON

Zamiast:
```json
{
  "destination": "Prague",
  "days": 4,
  "budget": "Mid"
}
```

Używamy `separators=(",",":")`:
```json
{"destination":"Prague","days":4,"budget":"Mid"}
```

Oszczędność: ~15-20% tokenów na whitespace.

### 7.2 Truncation kontekstu

Każdy agent dostaje skrócone outputy poprzednich agentów:
```python
"profile_summary": _truncate(state["profile_summary"], limit=600)
"geo_markdown": _truncate(state["geo_markdown"], limit=1200)
```

### 7.3 Compact representations

Geo output dla itinerary_agent jest kompaktowy:
```python
compact_geo = {
    "mobility_strategy": "public transport",
    "days": [
        {"day": 1, "title": "Old Town", "morning_place": "...", "afternoon_place": "...", "evening_place": "..."}
    ]
}
```

Zamiast pełnego `GeoOutput` z coordinates, addresses, TripAdvisor data (które itinerary nie potrzebuje).

### 7.4 Równoległy pipeline

`profile_agent` i `transport_agent` działają równolegle — nie oszczędza tokenów, ale oszczędza czas (latency).

---

## 8. AI Cost & Cache Dashboard — wizualizacja tokenów

Dashboard (`http://localhost:5173`) pokazuje:

### Token Cost Comparison (tiktoken)
- Wklej request + response → zobacz koszt na 8 modelach
- Horizontal bar chart sorted cheap → expensive
- Savings % vs najdroższy model
- Pricing table z datą aktualizacji

### Real Pipeline Token Usage (z token_usage.json)
- Stacked bar chart per agent (input + output)
- Tabela z % udziałem każdego agenta
- Model i provider info
- Elapsed seconds per agent

### Auto-push z TravelMate
- Po każdym tripie TravelMate automatycznie pushuje dane do dashboardu
- RunPicker z listą wszystkich runów
- Live badge dla nowo pushniętych runów

---

## 9. Znane ograniczenia

1. **Gemini usage_metadata** — Google API czasem nie zwraca tokenów w response; tracker pokazuje 0. Obejście: szacowanie na podstawie długości tekstu × współczynnik.

2. **tiktoken vs inne tokenizery** — Dashboard używa cl100k_base (GPT-4). Dla Gemini i Claude tokeny mogą się różnić o ±10%. To jest zaznaczone disclaimerem w UI.

3. **System prompt nie jest widoczny** — Token tracker liczy input_tokens jako sumę (system + task + human message). Nie rozdziela ile z tego to prompt a ile dane.

4. **Cached tokens** — Niektóre API (Anthropic, OpenAI) zwracają też `cache_creation_input_tokens` i `cache_read_input_tokens`. Obecny tracker ich nie obsługuje (TODO dla produkcji).

---

*Dokument: TOKEN_COUNTING.md | Wersja: 1.0 | Data: 2026-06-11*
