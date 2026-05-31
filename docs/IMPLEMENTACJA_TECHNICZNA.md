# TravelMate — Propozycja Implementacji Technicznej Architektury Produkcyjnej

> Dokument opisuje szczegółową koncepcję implementacji przejścia z POC do architektury produkcyjnej. Nie jest to kod do wdrożenia — to blueprint techniczny dla zespołu deweloperskiego. Wersja: 1.0 | Data: 2026-05-24

---

## 1. Kontekst i zakres

Dokument opisuje implementację następujących elementów produkcyjnych:

1. **Dynamiczny routing modeli LLM** — jeden flow, różne modele per tier złożoności
2. **Semantic Cache z PostgreSQL + pgvector** — trzy ścieżki: Full Hit, Partial Hit, Full Miss
3. **Security Guards** — Input Shield i Output Shield
4. **Query Enricher** — rozbudowanie zapytania przed pipeline'em
5. **Editorial Formatter** — redakcja końcowej odpowiedzi

Dokument zakłada znajomość architektury POC opisanej w `ARCHITEKTURA_PRODUKCYJNA.md`.

---

## 2. Dynamiczny routing modeli — koncepcja implementacji

### 2.1 Zasada działania

Kluczowa zasada: **jeden graf LangGraph, jeden zestaw agentów, dynamicznie wybierany model LLM per agent per zapytanie**.

Nie tworzymy oddzielnych flow dla różnych tierów złożoności. Zamiast tego, przed uruchomieniem pipeline'u, Complexity Router oblicza score złożoności i zapisuje do stanu LangGraph słownik `routing_config` — mapowanie agent → model_id. Każdy agent odczytuje swój model_id ze stanu i inicjalizuje odpowiedni klient LLM.

### 2.2 Complexity Router — logika oceny

Complexity Router to lekki agent (Gemini Flash) który ocenia zapytanie w sześciu wymiarach i przypisuje punkty:

**Wymiar 1: Liczba dni (0-20 pkt)**
- 1-3 dni: 5 pkt — krótki weekend, łatwy do zaplanowania
- 4-5 dni: 10 pkt — standardowy wyjazd
- 6-7 dni: 15 pkt — tygodniowy urlop, więcej logistyki
- 8+ dni: 20 pkt — długa wyprawa, złożona logistyka

**Wymiar 2: Liczba uczestników (0-15 pkt)**
- 1-2 osoby: 3 pkt
- 3-4 osoby: 8 pkt
- 5+ osób: 15 pkt — grupy wymagają koordynacji

**Wymiar 3: Specjalne wymagania/constraints (0-25 pkt)**
- Brak: 0 pkt
- 1-2 constraints: 8-16 pkt
- 3+ constraints: 25 pkt — np. "wegetarianie + dzieci + pies + dostępność dla wózka"

**Wymiar 4: Destynacja (0-20 pkt)**
- Popularne europejskie miasta (Praga, Rzym, Barcelona, Paryż): 5 pkt — model ma dużo wiedzy
- Mniej popularne europejskie: 10 pkt
- Egzotyczne/odległe (Japonia, Patagonia, Maroko): 20 pkt — model potrzebuje głębszego rozumowania

**Wymiar 5: Budżet (0-10 pkt)**
- Low: 0 pkt
- Mid: 5 pkt
- Luxury: 10 pkt — więcej opcji do rozważenia, wyższe oczekiwania

**Wymiar 6: Jakość zapytania (0-10 pkt)**
- Jasne, kompletne: 0 pkt
- Niejasne, wieloznaczne, brakujące parametry: 10 pkt

**Progi tierów:**
- 0-40 pkt → SIMPLE
- 41-70 pkt → STANDARD
- 71-100 pkt → COMPLEX

### 2.3 Routing Config — przypisanie modeli per tier

```
SIMPLE tier (score 0-40):
  Wszystkie agenty: gemini-2.5-flash
  Uzasadnienie: Popularne destynacje, krótkie wyjazdy — model Flash
  ma wystarczającą wiedzę i jest 10x tańszy od Sonnet.
  Szacowany koszt: $0.02-0.05 per zapytanie

STANDARD tier (score 41-70):
  profile_agent:      claude-haiku-4.5
  transport_agent:    claude-haiku-4.5
  geo_agent:          gpt-4o-mini
  itinerary_agent:    claude-sonnet-4.6   ← kluczowy agent, najlepszy model
  verification_agent: gpt-4o-mini
  formatter_agent:    claude-haiku-4.5
  Uzasadnienie: Itinerary to najważniejszy i najtrudniejszy krok —
  dostaje najlepszy model. Reszta może być tańsza.
  Szacowany koszt: $0.05-0.12 per zapytanie

COMPLEX tier (score 71-100):
  profile_agent:      claude-sonnet-4.6
  transport_agent:    claude-sonnet-4.6
  geo_agent:          gpt-4.1
  itinerary_agent:    claude-opus-4.6    ← deep reasoning dla złożonych przypadków
  verification_agent: claude-sonnet-4.6
  formatter_agent:    claude-sonnet-4.6
  Uzasadnienie: Złożone zapytania (Luxury + egzotyka + wiele constraints)
  wymagają modelu który potrafi jednocześnie balansować wiele zmiennych.
  Szacowany koszt: $0.15-0.35 per zapytanie
```

### 2.4 Jak model_factory obsługuje routing

Obecna implementacja `get_chat_model()` zawsze zwraca model z `.env`. W produkcji funkcja przyjmuje opcjonalny parametr `model_id`. Jeśli podany — inicjalizuje odpowiedni klient LLM dla danego providera. Jeśli nie — zachowanie jak teraz (backward compatible).

Mapowanie model_id → provider jest przechowywane w konfiguracji (nie w kodzie) — można dodawać nowe modele bez zmiany logiki agentów.

### 2.5 Zmiana w agentach — minimalna ingerencja

Każdy agent wymaga zmiany dokładnie jednej linijki: zamiast `get_chat_model()` wywołuje `get_chat_model(model_id=state["routing_config"]["nazwa_agenta"])`. Reszta kodu agenta pozostaje bez zmian — prompty, logika, parsowanie outputu.

To jest kluczowa zaleta Podejścia 1 — istniejący kod agentów jest w 99% niezmieniony.

### 2.6 Rozszerzenie PlannerState

Do istniejącego TypedDict PlannerState dodawane są trzy nowe pola:
- `complexity_score: int` — wynik 0-100 z Complexity Router
- `complexity_tier: str` — "simple" / "standard" / "complex"
- `routing_config: dict[str, str]` — słownik agent_name → model_id

Pola są opcjonalne (z defaultem None) dla backward compatibility z istniejącymi testami.

### 2.7 Aktualizacja grafu LangGraph

Complexity Router staje się pierwszym węzłem grafu, uruchamianym przed profile_agent i transport_agent. Ponieważ jest lekki (~200ms), nie wpływa znacząco na całkowity czas pipeline'u.

Graf po zmianie:
```
START → complexity_router → profile_agent (równolegle)
                          → transport_agent (równolegle)
        → fan_in → geo_agent → itinerary_agent → verification_agent → formatter_agent → END
```

---

## 3. Semantic Cache — koncepcja implementacji

### 3.1 Warstwa danych — PostgreSQL + pgvector

**Dlaczego PostgreSQL a nie dedykowana baza wektorowa (Pinecone, Qdrant)?**

TravelMate przechowuje nie tylko wektory ale też strukturalne dane (request_params jako JSONB, daty, destynacje). PostgreSQL pozwala na filtrowanie po tych polach PRZED wyszukiwaniem wektorowym — co znacząco przyspiesza ANN search przy dużej liczbie wpisów. Dedykowane bazy wektorowe wymagałyby osobnej bazy SQL dla danych strukturalnych.

Przy skali 1000 req/dzień i TTL 90 dni — maksymalnie ~90 000 wpisów w cache. PostgreSQL z indeksem HNSW obsługuje to bez problemu (czas query < 20ms).

**Schemat przechowywanych danych:**

Każdy wpis w cache zawiera:
- Wektor embeddingu zapytania (1536 wymiarów)
- Oryginalne zapytanie tekstowe
- Parametry requestu jako JSONB (destination, days, budget, pace, interests, constraints)
- Outputy każdego agenta osobno (profile_summary, transport_report, geo_output, itinerary_draft)
- Finalny plan w Markdown
- Metadane: created_at, expires_at, hit_count, last_hit_at, destination (dla filtrowania), language

**Indeksowanie:**
- Indeks HNSW na kolumnie embedding (parametry: m=16, ef_construction=64) — optymalny dla recall/speed tradeoff przy tej skali
- Indeks B-tree na (destination, is_active) — dla pre-filtrowania przed ANN search
- Indeks B-tree na expires_at — dla automatycznego czyszczenia wygasłych wpisów

### 3.2 Embedding Model — wybór i uzasadnienie

Rekomendacja: `text-embedding-3-small` (OpenAI) — 1536 wymiarów, koszt $0.02/1M tokenów.

Alternatywa: `text-embedding-004` (Google) — podobna jakość, może być tańsza przy dużym wolumenie.

Ważne: model embeddingowy musi być stały przez cały czas życia cache. Zmiana modelu wymaga re-embeddingu wszystkich wpisów (migracja). Dlatego wybór modelu embeddingowego jest decyzją długoterminową.

### 3.3 Trzy ścieżki — szczegółowa logika decyzyjna

**Cache Decision Engine** to komponent aplikacyjny (Python, bez LLM) który po otrzymaniu wyników ANN search decyduje o ścieżce:

**Ścieżka A — Full Hit:**
Warunki: similarity ≥ 0.88 ORAZ wszystkie kluczowe parametry identyczne (destination, days ±0, budget, pace, interests ≈ 80% overlap).
Akcja: Zwróć response_md z cache. Uruchom tylko Formatter Agent dla dostosowania stylu.
Zaktualizuj hit_count i last_hit_at w bazie.

**Ścieżka B — Partial Hit:**
Warunki: similarity ≥ 0.70 ORAZ przynajmniej destination identyczna.
Akcja: Uruchom Cache Decomposer który analizuje różnice i decyduje które komponenty są reużywalne.

Cache Decomposer sprawdza każdy komponent według reguł:
- profile_summary: reużywalny jeśli pace i budget identyczne, interests ≥ 70% overlap
- transport_report: reużywalny jeśli home_location i destination identyczne
- geo_output: reużywalny jeśli destination identyczna (HERE data ma własny TTL)
- itinerary_draft: wymaga odświeżenia jeśli days różni się o więcej niż 1, lub budget zmieniony, lub constraints zmienione

Agenci których komponenty są reużywalne są pomijane — ich output jest pobierany z cache i wstrzykiwany do stanu LangGraph. Pozostałe agenty uruchamiają się normalnie, ale dostają jako wejście dane z cache (np. itinerary_agent dostaje geo_output z bazy zamiast czekać na geo_agent).

Po zakończeniu Partial Hit — nowy wpis jest zapisywany do cache (nowe zapytanie + nowy output).

**Ścieżka C — Full Miss:**
Warunki: similarity < 0.70 lub brak wpisów dla danej destynacji.
Akcja: Pełny pipeline od zera. Po zakończeniu — Cache Writer zapisuje wszystkie komponenty do bazy.

### 3.4 TTL Strategy — jak długo przechowywać dane

Różne typy wiedzy mają różną "świeżość":

| Komponent | TTL | Uzasadnienie |
|---|---|---|
| geo_output (strefy, HERE data) | 90 dni | Atrakcje i adresy zmieniają się rzadko |
| profile_summary | 90 dni | Archetypy podróżników są stabilne |
| transport_report (opcje ogólne) | 30 dni | Ceny lotów zmieniają się częściej |
| transport_report (konkretne daty) | 1 dzień | Ceny na konkretne daty są zmienne |
| itinerary_draft | 30 dni | Plan może być nieaktualny po miesiącu |
| response_md (finalny plan) | 30 dni | Jak itinerary |

Implementacja: pole `expires_at` per wpis. Cache Writer ustawia TTL na podstawie parametrów zapytania (czy podano konkretne daty → krótszy TTL).

### 3.5 Cache Invalidation — jak unieważniać wpisy

Trzy mechanizmy:
1. **Automatyczny TTL** — wpisy wygasają automatycznie, background job czyści je co noc
2. **Manual invalidation endpoint** — `DELETE /cache/destination/{city}` dla administratora (np. gdy atrakcja zamknięta)
3. **Confidence-based invalidation** — jeśli verification_agent wykryje że cached dane są nieaktualne (np. muzeum zamknięte), oznacza wpis jako is_active=FALSE

---

## 4. Security Guards — koncepcja implementacji

### 4.1 Input Shield — co sprawdza i jak

Input Shield to pierwszy krok pipeline'u, uruchamiany przed Complexity Router. Używa małego, szybkiego modelu (Gemini Flash lub GPT-4o-mini).

**Cztery kategorie sprawdzeń:**

**Kategoria 1: Prompt Injection Detection**
Regex-based pre-screening (bez LLM, < 1ms) dla oczywistych wzorców:
- "ignore previous instructions"
- "you are now", "act as if"
- "DAN mode", "jailbreak"
- Tagi systemowe: `<system>`, `[INST]`, `###instruction`

Jeśli regex wykryje wzorzec → natychmiastowa blokada bez wywołania LLM.

Dla subtelniejszych przypadków → LLM classifier z binarnym outputem (SAFE/UNSAFE) i poziomem ryzyka (none/low/medium/high/critical).

**Kategoria 2: PII Detection**
Wykrywanie danych osobowych w zapytaniu:
- Numery kart kredytowych (regex)
- PESEL, numery paszportów (regex)
- Hasła i tokeny (regex: "password:", "api_key:", "sk-")
- Adresy email i numery telefonów (regex)

Akcja: Sanityzacja (usunięcie PII) zamiast blokady — zapytanie jest oczyszczane i przekazywane dalej.

**Kategoria 3: Content Policy**
LLM classifier sprawdza czy zapytanie jest rzeczywiście o podróży:
- Treści nielegalne lub szkodliwe → blokada
- Zapytania niezwiązane z podróżami → odrzucenie z przyjaznym komunikatem
- Zapytania o podróże → przepuszczenie

**Kategoria 4: Rate Limiting**
Sprawdzenie w Redis (nie PostgreSQL — szybkość):
- Per IP: max 10 req/min
- Per user_id: max 100 req/dzień (free tier), 500 req/dzień (premium)
- Per session: max 5 concurrent requests

**Output Input Shield:**
```
SecurityCheckResult:
  passed: bool
  risk_level: "none" | "low" | "medium" | "high" | "critical"
  blocked_reason: str | None  (tylko do logów, nie do użytkownika)
  sanitized_input: str        (oczyszczone zapytanie)
```

Użytkownik nigdy nie dowiaduje się dlaczego zapytanie zostało zablokowane — tylko generyczny komunikat "Nie mogę przetworzyć tego zapytania".

### 4.2 Output Shield — co sprawdza i jak

Output Shield uruchamia się po formatter_agent, przed wysłaniem odpowiedzi do użytkownika.

**Trzy kategorie sprawdzeń:**

**Kategoria 1: Data Leakage Detection**
Regex sprawdza czy output nie zawiera:
- Kluczy API (wzorce: sk-, AIza, ant-)
- Ścieżek systemowych (/Users/, /home/, C:\)
- Wewnętrznych nazw zmiennych i klas (SYSTEM_PROMPT, PlannerState)
- Danych z innych użytkowników (cross-contamination)

**Kategoria 2: Role Escape Detection**
LLM classifier sprawdza czy model "uciekł" z roli travel plannera:
- Czy output jest faktycznie planem podróży?
- Czy nie zawiera instrukcji niezwiązanych z podróżą?
- Czy nie próbuje wykonać kodu lub poleceń?

**Kategoria 3: Hallucination Check (podstawowy)**
Weryfikacja podstawowych faktów:
- Czy destynacja w outputcie zgadza się z requestem?
- Czy liczba dni w planie zgadza się z requestem?
- Czy daty (jeśli podane) są logiczne?

Akcja przy wykryciu: Sanityzacja (usunięcie problematycznej sekcji) lub fallback do baseline_markdown (deterministyczny output bez LLM).

---

## 5. Query Enricher — koncepcja implementacji

### 5.1 Cel i zakres

Query Enricher uruchamia się po Complexity Router, przed profile_agent i transport_agent. Jego zadaniem jest wzbogacenie zapytania o kontekst który poprawi jakość wszystkich kolejnych agentów.

### 5.2 Co dodaje

**Kontekst sezonowy:**
Na podstawie travel_start_date (lub bieżącego miesiąca jeśli brak) dodaje informacje o:
- Pogodzie w destynacji w danym sezonie
- Tłumach turystycznych (peak/off-season)
- Lokalnych świętach i wydarzeniach
- Specyficznych warunkach (monsun, upały, mróz)

Przykład: "Tokio, lipiec" → dodaje "Lipiec w Tokio: bardzo gorąco (35°C+), wysoka wilgotność, tłumy turystów, festiwal Obon w połowie miesiąca — wiele atrakcji zamkniętych lub przepełnionych"

**Kontekst kulturowy:**
- Ramadan w krajach muzułmańskich → restauracje zamknięte w dzień
- Dni wolne od pracy w destynacji → muzea zamknięte
- Lokalne zwyczaje istotne dla planowania (np. sjesta w Hiszpanii)

**Normalizacja destynacji:**
- "Praga" → "Prague, Czech Republic" (dla HERE Maps API)
- "Góry Stołowe" → "Stołowe Mountains, Lower Silesia, Poland"
- Ujednolicenie nazewnictwa dla lepszego geo_agent output

**Uzupełnienie brakujących parametrów:**
- Brak home_location → dodaje "home_location: unknown — transport report will note this"
- Brak dat → dodaje "no specific dates — seasonal recommendations based on current month"
- Brak accommodation_area → sugeruje na podstawie interests i budget

**Output Query Enricher:**
Wzbogacony `ItineraryInput` + lista `enrichment_notes` (co zostało dodane i dlaczego) — te notatki są przekazywane do agentów jako dodatkowy kontekst.

---

## 6. Editorial Formatter — koncepcja implementacji

### 6.1 Różnica względem obecnego formatter_agent

Obecny formatter_agent w POC:
- Składa outputy wszystkich agentów w jeden Markdown
- Sprawdza spójność (destination match, days count)
- Dodaje sekcję POI z HERE/TripAdvisor data

Editorial Formatter w produkcji dodaje:
- Dostosowanie tonu do kontekstu (B2C vs B2B, język użytkownika)
- "Quick View" summary na początku (3-5 zdań)
- Sekcja "Pro Tips" na końcu (3-5 praktycznych wskazówek)
- Spójność językowa (cały plan w jednym języku)
- Formatowanie dla różnych outputów (Markdown dla B2C, JSON dla B2B API)

### 6.2 B2C vs B2B formatting

**B2C output:**
- Emoji w nagłówkach (🗺️ 📅 🏨 ✈️)
- Przyjazny, konwersacyjny ton
- "Quick View" na początku
- "Pro Tips" na końcu
- Pełny Markdown z tabelami i listami

**B2B API output:**
- Czysty JSON z ustrukturyzowanymi danymi
- Bez emoji
- Profesjonalny ton
- Pola: destination, days, itinerary (array), transport_options, geo_points, warnings
- Kompatybilny z systemami OTA i booking engines

---

## 7. Integracja wszystkich komponentów — pełny flow

### 7.1 Sekwencja kroków w produkcji

```
1. Request przychodzi do FastAPI
2. API Gateway sprawdza auth (JWT/API Key) i rate limit
3. Input Shield (Security Guard) — ~200ms
   a. Regex pre-screening (< 1ms)
   b. LLM classifier jeśli potrzebny (~150ms)
   c. PII sanitization
   → BLOCK lub PASS z sanitized_input
4. Semantic Cache Lookup — ~15ms
   a. Embedding zapytania (~50ms, równolegle z krokiem 3b)
   b. ANN search w PostgreSQL
   c. Cache Decision Engine
   → Full Hit / Partial Hit / Full Miss
5a. Full Hit path:
   → Formatter Agent (~500ms)
   → Output Shield (~200ms)
   → Response (total: ~1s)
5b. Partial Hit path:
   → Cache Decomposer (Python, < 10ms)
   → Complexity Router (~300ms)
   → Query Enricher (~500ms)
   → Selective agents (2-4 agentów, ~8-15s)
   → Output Shield (~200ms)
   → Cache Writer (async, nie blokuje response)
   → Response (total: ~10-17s)
5c. Full Miss path:
   → Complexity Router (~300ms)
   → Query Enricher (~500ms)
   → profile_agent + transport_agent (równolegle, ~3-6s)
   → geo_agent (~5-8s)
   → itinerary_agent (~6-15s zależnie od modelu)
   → verification_agent (~3-6s)
   → Output Shield (~200ms)
   → Editorial Formatter (~1-3s)
   → Cache Writer (async)
   → Response (total: ~20-40s)
```

### 7.2 Asynchroniczny Cache Writer

Cache Writer działa asynchronicznie — nie blokuje wysłania odpowiedzi do użytkownika. Po wysłaniu response, w tle:
1. Generuje embedding zapytania (jeśli nie był wygenerowany wcześniej)
2. Zapisuje wszystkie komponenty do PostgreSQL
3. Loguje metryki (koszt, czas, tier, cache decision)

### 7.3 Obsługa błędów i fallback

Każdy komponent ma zdefiniowany fallback:
- Input Shield fail → przepuść zapytanie (fail open) z logiem
- Cache Lookup fail → traktuj jako Full Miss
- Complexity Router fail → użyj STANDARD tier jako default
- Query Enricher fail → użyj oryginalnego zapytania bez wzbogacenia
- Agent LLM fail → użyj fallback (jak w POC: baseline_markdown dla formatter)
- Output Shield fail → przepuść output z logiem (fail open)
- Cache Writer fail → zaloguj błąd, nie blokuj response

Zasada: **żaden komponent nie może zablokować odpowiedzi do użytkownika** — każdy ma fallback który pozwala kontynuować.

---

## 8. Monitoring i observability — co mierzyć

### 8.1 Metryki per request (do logowania)

Każde zapytanie generuje log z:
- request_id (UUID)
- user_id / session_id
- complexity_score i complexity_tier
- cache_decision (full_hit / partial_hit / full_miss)
- cache_similarity_score
- agents_run (lista agentów które faktycznie się uruchomiły)
- models_used (słownik agent → model_id)
- token_usage per agent (input, output, total)
- elapsed_seconds per agent
- total_cost_usd
- total_elapsed_seconds
- security_events (lista jeśli były)

### 8.2 Agregowane metryki (dashboardy)

**Cost Dashboard:**
- Średni koszt per tier (Simple/Standard/Complex)
- Cache hit rate (cel: > 40%)
- Szacowane oszczędności z cache (vs brak cache)
- Top 10 najdroższych zapytań

**Performance Dashboard:**
- Latency P50/P95/P99 per ścieżka (Full Hit / Partial Hit / Full Miss)
- Latency per agent per tier
- Error rate per agent

**Security Dashboard:**
- Blocked requests per hour
- Injection attempts per day
- Output shield triggers
- Top blocked IPs

**Business Dashboard:**
- Najpopularniejsze destynacje
- Rozkład tierów (ile % Simple/Standard/Complex)
- Cache hit rate per destynacja
- DAU/MAU (B2C)

---

## 9. Migracja z POC do produkcji — kolejność kroków

### Faza 1 — Fundament (bez zmiany UX, 4-6 tygodni)
1. PostgreSQL + pgvector setup na Azure
2. Schemat bazy danych + indeksy
3. Embedding pipeline (generowanie wektorów)
4. Cache Lookup (tylko read, bez write)
5. Cache Writer (async write po każdym Full Miss)
6. Monitoring podstawowy (logi per request)

Po Fazie 1: System działa jak POC ale zbiera dane do cache. Użytkownik nie widzi różnicy.

### Faza 2 — Cache aktywny (4-6 tygodni)
1. Cache Decision Engine (Full Hit path)
2. Complexity Router Agent
3. Rozszerzenie model_factory o model_id param
4. Aktualizacja agentów (1 linijka per agent)
5. Aktualizacja grafu LangGraph
6. A/B test: 10% ruchu przez nowy system, 90% przez stary

Po Fazie 2: Cache działa dla Full Hit. Complexity Router wybiera modele. Koszty zaczynają spadać.

### Faza 3 — Partial Hit + Security (3-4 tygodnie)
1. Cache Decomposer
2. Partial Hit path w pipeline
3. Input Shield (regex + LLM classifier)
4. Output Shield
5. Query Enricher
6. Editorial Formatter

Po Fazie 3: Pełna architektura produkcyjna aktywna.

### Faza 4 — Hardening (3-4 tygodnie)
1. Azure API Management (rate limiting, auth)
2. Azure AD B2C (B2C auth)
3. B2B API endpoints
4. Load testing (1000 req/dzień)
5. Security penetration testing
6. SLA documentation

---

## 10. Decyzje techniczne do podjęcia przed implementacją

1. **Embedding model**: text-embedding-3-small (OpenAI) vs text-embedding-004 (Google) — decyzja długoterminowa, zmiana wymaga re-embeddingu całej bazy

2. **Cache granularity**: Czy cache przechowuje outputy per agent osobno (bardziej elastyczne dla Partial Hit) czy tylko finalny response (prostsze)? Rekomendacja: per agent, ale wymaga więcej miejsca w bazie

3. **Similarity threshold**: 0.88 dla Full Hit i 0.70 dla Partial Hit — wartości do kalibracji na podstawie danych produkcyjnych po Fazie 1

4. **Cache scope**: Globalny (jeden cache dla wszystkich użytkowników) vs per-user (personalizacja). Globalny = wyższy hit rate, per-user = lepsza personalizacja ale niższy hit rate. Rekomendacja: globalny z opcją per-user dla premium tier

5. **Llama 3 / open source models**: Czy warto dodać Llama 3 (via Groq lub Together) dla SIMPLE tier? Potencjalnie tańszy niż Gemini Flash, ale wymaga dodatkowej integracji i testów jakości

---

*Dokument: IMPLEMENTACJA_TECHNICZNA.md | Wersja: 1.0 | Data: 2026-05-24*
