# Wektoryzacja, AI Act i Build vs Buy — Dokumentacja decyzji

> Dokument odpowiada na trzy kluczowe pytania architektoniczne: jaki model embeddingowy wybrać, jak spełnić wymogi AI Act, i dlaczego budujemy zamiast kupować. Wersja: 1.0 | Data: 2026-06-11

---

## 1. Model embeddingowy — wybór i uzasadnienie

### 1.1 Co robi model embeddingowy?

Model embeddingowy zamienia tekst na wektor liczbowy (listę 768-3072 liczb). Ten wektor reprezentuje "znaczenie" tekstu w przestrzeni wielowymiarowej. Podobne teksty → podobne wektory → cosine similarity blisko 1.0.

W TravelMate embedding jest używany do:
- **Cache lookup** — czy podobne zapytanie już było?
- **Cache Relevance Check** — czy cached plan pasuje do nowego zapytania?
- **Places Graph** (docelowo) — wyszukiwanie podobnych miejsc

### 1.2 Porównanie modeli embeddingowych

| Model | Provider | Wymiary | Koszt/1M tok | MTEB Score | PL support | Latency |
|---|---|---|---|---|---|---|
| **text-embedding-3-small** | OpenAI | 1536 | $0.02 | 62.3% | ✅ Dobry | ~50ms |
| text-embedding-3-large | OpenAI | 3072 | $0.13 | 64.6% | ✅ Dobry | ~80ms |
| text-embedding-004 | Google | 768 | $0.00* | 66.3% | ✅ Dobry | ~40ms |
| embed-v4 | Cohere | 1024 | $0.10 | 66.1% | ✅ | ~60ms |
| voyage-3 | Voyage AI | 1024 | $0.06 | 67.1% | ⚠️ Średni | ~70ms |
| all-MiniLM-L6-v2 | HuggingFace (local) | 384 | $0 | 49.5% | ❌ Słaby PL | ~5ms |
| multilingual-e5-large | HuggingFace (local) | 1024 | $0 | 61.5% | ✅ | ~20ms |

*Google: free tier do 1500 req/min, potem $0.025/1M

### 1.3 Rekomendacja: text-embedding-3-small (OpenAI)

**Dlaczego ten model:**

1. **Multilingual** — TravelMate dostaje zapytania PL i EN (mix). Model dobrze radzi sobie z oboma.
2. **Koszt** — $0.02/1M tokenów. Przy 1000 req/dzień i ~50 tokenów per embedding = 50K tokenów/dzień = **$0.001/dzień = $0.03/miesiąc**. Pomijalne.
3. **1536 wymiarów** — optymalny balans jakość/rozmiar. W PostgreSQL pgvector index HNSW na VECTOR(1536) jest szybki do ~500K wpisów.
4. **Stabilność API** — OpenAI nie usunie tego modelu z dnia na dzień (committed, miliony klientów).
5. **Jakość 62.3% MTEB** — wystarczająca dla cache lookup (nie robimy RAG na dokumentach, tylko similarity search na krótkich zapytaniach o podróże).

**Dlaczego nie inne:**

| Odrzucony | Powód |
|---|---|
| text-embedding-3-large | 2x droższy, 2x większy wektor, marginalnie lepsza jakość (62.3→64.6) — nie warto dla cache |
| Google text-embedding-004 | 768 wymiarów — niższa precyzja cache hit/miss. Free tier ale ryzyko zmian w API |
| all-MiniLM-L6-v2 (local) | Słaby na polskim (49.5%). Szybki i darmowy ale niedostateczna jakość |
| multilingual-e5-large | Dobry na PL, ale wymaga hostowania GPU (~$200/mies). Nie warto przy koszcie API $0.03/mies |

### 1.4 Jak wektoryzujemy — techniczny flow

```
1. Zapytanie użytkownika przychodzi
   "5 dni w Pradze, Mid, piwo i historia"

2. Sanityzacja (Input Shield usunął PII/injection)
   "5 dni w Pradze, Mid, piwo i historia" (czyste)

3. Embedding API call
   POST https://api.openai.com/v1/embeddings
   {
     "model": "text-embedding-3-small",
     "input": "5 dni w Pradze, Mid, piwo i historia",
     "encoding_format": "float"
   }

4. Odpowiedź: wektor 1536 float
   [0.023, -0.087, 0.041, 0.012, -0.033, ... ] (1536 wartości)

5. Zapis do PostgreSQL
   INSERT INTO semantic_cache (query_embedding) VALUES ($vector);
   
6. Wyszukiwanie (przy następnym zapytaniu)
   SELECT ... ORDER BY query_embedding <=> $new_vector LIMIT 5;
```

### 1.5 Ważne zasady

- **Jeden model** na cały czas życia cache. Zmiana modelu = re-embedding WSZYSTKICH wpisów (migracja).
- **Nie mieszaj modeli** — embedding z text-embedding-3-small NIE jest kompatybilny z embedding z Google text-embedding-004.
- **Normalizacja** — OpenAI zwraca znormalizowane wektory (length=1.0), co upraszcza cosine similarity do dot product.
- **Batching** — wysyłaj do 100 tekstów w jednym API call (oszczędność na overhead HTTP).

### 1.6 Koszt embeddingów przy skali

| Skala | Embeddingi/dzień | Koszt/dzień | Koszt/miesiąc |
|---|---|---|---|
| 100 req/dzień | ~100 | $0.0001 | $0.003 |
| 1 000 req/dzień | ~600* | $0.0006 | $0.018 |
| 10 000 req/dzień | ~4 000* | $0.004 | $0.12 |

*60% = cache miss (nowy embedding), 40% = cache hit (nie potrzebuje nowego, bo już mamy embedding zapytania)

**Wniosek**: Koszt embeddingów jest POMIJALNE — $0.12/mies nawet przy 10K req/dzień. To nie jest bottleneck kosztowy.

---

## 2. EU AI Act — jak to ogarnąć dla TravelMate

### 2.1 Klasyfikacja ryzyka TravelMate

EU AI Act klasyfikuje systemy AI w 4 kategoriach ryzyka:

| Kategoria | Przykłady | TravelMate? |
|---|---|---|
| **Niedopuszczalne** | Social scoring, manipulacja podprogowa | ❌ Nie |
| **Wysokie ryzyko** | Medycyna, rekrutacja, prawo, transport autonomiczny | ❌ Nie |
| **Ograniczone ryzyko** | Chatboty, generatory tekstu, systemy rekomendacji | ✅ **TAK** |
| **Minimalne ryzyko** | Filtry spam, gry | ❌ Nie |

**TravelMate = ograniczone ryzyko (limited risk)**. To najłagodniejsza kategoria która wymaga compliance.

### 2.2 Wymagania AI Act dla ograniczonego ryzyka

| Wymóg | Co to znaczy | Jak spełniamy |
|---|---|---|
| **Transparentność** | Użytkownik wie że rozmawia z AI | UI wyraźnie mówi "TravelMate AI", "AI-generated plan" |
| **Oznaczanie treści AI** | Output oznaczony jako generowany przez AI | Footer: "Plan wygenerowany przez AI. Zweryfikuj szczegóły." |
| **Nie wprowadzanie w błąd** | System nie udaje człowieka | Brak "jestem ludzkim konsultantem" |
| **Informacja o ograniczeniach** | Użytkownik wie że AI może się mylić | Sekcja "⚠️ Weryfikacja" w każdym planie |
| **Sponsorowane treści** | Reklamy oznaczone jako reklamy | Badge "Oferta sponsorowana" obok płatnych rekomendacji |
| **Prawo do wyjaśnienia** | Użytkownik może zapytać dlaczego | "Dlaczego ta rekomendacja?" → krótkie wyjaśnienie logiki |

### 2.3 Implementacja techniczna

#### A) UI oznaczenia

```html
<!-- Header czatu -->
<div class="ai-badge">🤖 TravelMate AI — asystent podróży</div>

<!-- Każda odpowiedź -->
<div class="ai-disclaimer">
  Plan wygenerowany automatycznie przez AI. 
  Godziny otwarcia, ceny i dostępność mogą się zmienić — zweryfikuj przed podróżą.
</div>

<!-- Oferty sponsorowane (docelowo) -->
<div class="sponsored-badge">📢 Oferta partnerska</div>
```

#### B) Metadata w API response (B2B)

```json
{
  "plan": {...},
  "metadata": {
    "generated_by": "travelmate-ai-v2",
    "model_used": "gemini-2.5-flash",
    "ai_generated": true,
    "confidence_notes": ["Opening hours require verification", "Prices are estimates"],
    "sponsored_items": [],
    "generation_timestamp": "2026-06-11T14:30:00Z"
  }
}
```

#### C) Human oversight

- Admin panel z możliwością review wygenerowanych planów
- Flag system — użytkownicy mogą zgłosić "ten plan jest błędny"
- Manual override — admin może wyłączyć wpis z cache

### 2.4 Czego AI Act NIE wymaga od nas

- Nie musimy rejestrować systemu w EU database (to tylko high-risk)
- Nie musimy robić conformity assessment (to tylko high-risk)
- Nie musimy mieć "human in the loop" dla każdego planu (to nie jest decyzja o prawach osoby)
- Nie musimy udostępniać kodu źródłowego

### 2.5 Ryzyka prawne do monitorowania

| Ryzyko | Kiedy dotyczy | Mitygacja |
|---|---|---|
| Reklamy ukryte jako rekomendacje | Gdy dodamy oferty sponsorowane | Zawsze oznaczaj badge "Sponsorowane" |
| Dyskryminacja w rekomendacjach | Gdyby model faworyzował hotele/restauracje jednego łańcucha | Audit randomized responses, diversity check |
| Zbieranie danych nadmiarowe | Gdybyśmy logowali raw zapytania z PII | PII detection + hash zamiast raw text w cache |
| Brak informacji o AI | Gdyby użytkownik myślał że pisze z człowiekiem | Jasne oznaczenia "AI" w UI |

---

## 3. Build vs Buy — uzasadnienie decyzji

### 3.1 Czym jest decyzja Build vs Buy?

"Czy budujemy własną platformę od zera, czy kupujemy/integrujemy gotowe rozwiązanie?"

### 3.2 Dostępne opcje "Buy"

| Produkt | Co oferuje | Cena | Ograniczenia |
|---|---|---|---|
| TripIt (SAP Concur) | Organizacja podróży, parsing emaili | $49/rok per user | Brak AI generacji planów, enterprise-focused |
| Wonderplan AI | AI trip planner | Freemium | Zamknięte API, brak white-label, ograniczone destynacje |
| Roam Around | AI trip generator | $10/mies | Brak API, brak B2B, ograniczona customizacja |
| Layla AI | Conversational trip planner | Closed beta | Brak dostępu API, vendor lock-in |
| ChatGPT / Claude direct | General AI | Per token | Brak domain logic, brak cache, brak map, brak POI data |
| Google Travel AI | Wbudowane w Google | Brak API | Kompletny vendor lock-in, brak customizacji |

### 3.3 Dlaczego Build

| Argument | Wyjaśnienie |
|---|---|
| **Pełna kontrola nad pipeline'em AI** | Wybieramy modele, prompty, routing — nikt nam nie narzuca. Optymalizujemy koszty jak chcemy. |
| **Własne dane = moat** | Semantic cache, Places Graph, user behavior — to nasze dane. Nie dzielimy ich z platformą. |
| **B2B API jako produkt** | Sprzedajemy API innym firmom. Gdybyśmy "kupowali" — odsprzedawalibyśmy czyjąś usługę z marżą. |
| **Brak vendor lock-in** | Zmiana modelu LLM = 1 linijka kodu. Gdybyśmy byli na Wonderplan/Layla — migracja = budowa od zera. |
| **Koszty LLM spadają** | Ceny tokenów spadają ~50%/rok. Własna infrastruktura = pełne savings. Na cudzej platformie = ich savings, nie nasze. |
| **Personalizacja** | Możemy dowolnie kształtować UX, flow, prompty, cache logic. Na cudzej platformie = ich roadmapa. |
| **Pozycja negocjacyjna** | Jako właściciel technologii negocjujesz z inwestorem/partnerami z pozycji siły. |
| **IP (Intellectual Property)** | Cały kod, prompty, architecture, Places Graph — to jest IP firmy. Wartość przy exit/rundzie. |

### 3.4 Dlaczego NIE Buy

| Argument "za Buy" | Kontrargument |
|---|---|
| "Szybciej na rynku" | POC działa w 2 dni. Produkcja w 18 tygodni. "Buy" i tak wymaga integracji. |
| "Mniejszy zespół" | Przy "Buy" potrzebujesz integratorów + support od vendora. Nie zawsze taniej. |
| "Mniejsze ryzyko techniczne" | Ryzyko przenosimy na vendor lock-in i ryzyko że vendor zamknie usługę. |
| "Gotowe rozwiązanie" | Żadne gotowe rozwiązanie nie ma: multi-model routing, semantic cache z validation, Places Graph. Musielibyśmy i tak dużo budować. |

### 3.5 Co "kupujemy" (Buy) w architekturze Build

Nie budujemy WSZYSTKIEGO. Kupujemy commodity:

| Kupujemy (Buy) | Od kogo | Dlaczego |
|---|---|---|
| Modele LLM (API) | OpenAI, Anthropic, Google | Nie trenujemy własnych modeli — za drogie |
| Embeddings (API) | OpenAI | $0.02/1M tok, nie warto budować własnego |
| Mapy i POI | HERE Maps, TripAdvisor | Dane kartograficzne = miliardy $$ do zebrania |
| Cloud hosting | Azure | Nie budujemy własnego data center |
| Auth | Azure AD B2C | Nie budujemy własnego OAuth provider |
| Monitoring | Azure Monitor | Commodity, nie ma sensu budować od zera |

**Budujemy (Build) tylko to co daje przewagę konkurencyjną:**
- Pipeline AI (routing, prompty, agenci)
- Semantic cache z validation
- Places Graph
- B2B API z billing
- UX/frontend

### 3.6 Kiedy zmienilibyśmy decyzję na Buy?

| Scenariusz | Akcja |
|---|---|
| Google/OpenAI wypuszcza "Travel Planning API" z pełnym pipeline | Rozważ integrację zamiast własnych agentów |
| Pojawia się platforma z otwartym API + white-label | Rozważ jako alternatywę dla B2B klientów |
| Koszty utrzymania własnej platformy > 3x koszt Buy | Rozważ migrację na managed platform |

Na dzień dzisiejszy żadna z tych sytuacji nie zachodzi — Build jest słuszna decyzja.

---

*Dokument: EMBEDDING_AIACT_BUILDVSBUY.md | Wersja: 1.0 | Data: 2026-06-11*
