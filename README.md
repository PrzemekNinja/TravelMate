# TravelMate AI (LangGraph)

Aplikacja w Pythonie oparta o **LangGraph**, która generuje szczegółowy plan wycieczki dzień-po-dniu na podstawie preferencji użytkownika.

## Szybki start

1. Ustaw `MODEL_PROVIDER` i uzupełnij odpowiedni klucz API w `.env`.
2. Zainstaluj zależności z `requirements.txt`.
3. Uruchom CLI na danych wejściowych JSON.

Przykładowe uruchomienie:

`python -m travelmate.cli --input sample_input.json`

Nowy (i jedyny) interfejs GUI oparty o Tailwind + FastAPI + WebSocket uruchomisz tak:

`python -m travelmate.api.main`

W GUI użytkownik wpisuje wymagania **językiem naturalnym**. Aplikacja najpierw konwertuje je do ustrukturyzowanego formatu wejściowego (z ewentualnymi domyślnymi założeniami), a dopiero potem uruchamia agentów planujących.

Każda wygenerowana wycieczka jest automatycznie zapisywana do osobnego katalogu w `output/` jako pojedynczy plik HTML5 (`itinerary.html`) łączący opis i interaktywną mapę POI, plus kopia markdown (`itinerary.md`) i parametry wejścia (`request.json`).

Nowy interfejs ma układ 30/70 (konfigurator po lewej, plan po prawej), pasek nawigacyjny, pasek dni, oś czasu atrakcji i mapę.

Separacja warstw:

- `travelmate/web/` — frontend GUI (Tailwind + PWA assets)
- `travelmate/api/` — backend GUI (FastAPI + WebSocket)
- `travelmate/services/` — warstwa logiki aplikacyjnej (parse → planowanie → zapis)

Windows (1 klik):

- uruchom plik `run_gui.bat` z katalogu projektu.

## PWA / FastAPI Chat UI

Nowy interfejs webowy działa jako Progressive Web App i udostępnia:

- chatowy interfejs planowania podróży,
- panel `Admin_View` z logami i statusem agentów w czasie rzeczywistym,
- manifest i service worker do instalacji aplikacji.

Uruchomienie lokalne:

1. Upewnij się, że `.env` ma poprawnie ustawiony `MODEL_PROVIDER` i odpowiedni klucz API.
2. Zainstaluj zależności z `requirements.txt`.
3. Uruchom backend FastAPI:

  `python -m travelmate.api.main`

4. Otwórz w przeglądarce `http://127.0.0.1:8000`.

Wariant PWA korzysta z tego samego `PlannerService`, więc generuje takie same artefakty w `output/` jak CLI.

## Co robi aplikacja

Workflow jest podzielony na wyspecjalizowanych agentów:

1. `profile_agent` – buduje skrót profilu podróżnika.
2. `transport_agent` – przygotowuje raport transportowy „dom -> cel -> dom” (loty, kolej, wynajem auta, auto własne) z uwzględnieniem profilu i bagażu.
3. `geo_agent` – układa plan strefami/miejscami (Geo-Clustering) i wzbogaca każde miejsce danymi HERE (współrzędne, pełny adres, website).
4. `itinerary_agent` – generuje szczegółowy plan atrakcji i gastronomii.
5. `verification_agent` – sprawdza potencjalne ryzyka (np. godziny otwarcia).
6. `formatter_agent` – składa wynik do finalnego formatu Markdown.

## Struktura po refaktorze

- `travelmate/agents/` – każdy agent w osobnym pliku.
- `travelmate/prompts/` – prompty systemowe i taskowe per agent.
- `travelmate/tools/` – narzędzia pomocnicze (config, factory modelu, formatter markdown).
- `travelmate/graph.py` – tylko definicja i wiring grafu.

## Przełączanie modeli (OpenAI / Anthropic / Google / LM Studio)

W `.env` ustaw:

- `MODEL_PROVIDER=openai` albo `anthropic`, `google`, `lmstudio`
- odpowiedni model i klucz API dla wybranego providera

Przykład:

- OpenAI: `MODEL_PROVIDER=openai`, `OPENAI_API_KEY=...`
- Anthropic: `MODEL_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=...`
- Google: `MODEL_PROVIDER=google`, `GOOGLE_API_KEY=...`
- LM Studio: `MODEL_PROVIDER=lmstudio`, `LMSTUDIO_BASE_URL=http://localhost:1234/v1`

Opcjonalnie możesz podłączyć HERE Technology API, aby wzbogacić geo-planowanie o dane mapowe (geokodowanie + punkty POI):

- `HERE_API_KEY=...`
- `HERE_BASE_URL=https://geocode.search.hereapi.com/v1` (opcjonalny fallback)
- `HERE_GEOCODE_BASE_URL=https://geocode.search.hereapi.com/v1` (zalecane)
- `HERE_SEARCH_BASE_URL=https://discover.search.hereapi.com/v1` (zalecane; POI discover/lookup)

Po włączeniu HERE, dane `geo_output` zawierają dla **każdego miejsca dnia**:

- `coordinates`: `lat`, `lng`
- `address`: `country`, `city`, `postcode`, `street`, `building_number`
- `website`

Opcjonalnie możesz też podłączyć TripAdvisor Content API, aby dodać do każdego POI:

- 1 zdjęcie miejsca
- ocenę (rating)
- link do strony TripAdvisor

Konfiguracja (`.env`):

- `TRIPADVISOR_API_KEY=...`
- `TRIPADVISOR_BASE_URL=https://api.content.tripadvisor.com/api/v1` (opcjonalne)
- `TRIPADVISOR_LANGUAGE=en` (opcjonalne)
- `TRIPADVISOR_CURRENCY=USD` (opcjonalne)

## Dokumentacja

- `docs/ARCHITEKTURA.md` – opis komponentów, przepływu danych i decyzji projektowych.
- `docs/UZYCIE.md` – konfiguracja, uruchomienie, format wejścia/wyjścia, troubleshooting.
- `docs/ROZWOJ.md` – wskazówki dla deweloperów (rozbudowa agentów, testowanie, utrzymanie).
- `docs/DOKUMENTACJA_BIZNESOWA.md` – cele biznesowe, KPI, zakres produktu i roadmapa.
- `docs/DOKUMENTACJA_TECHNICZNA.md` – szczegóły implementacyjne, architektura runtime, logowanie i utrzymanie.

## Wymagania

- Python 3.11+
- Klucz OpenAI API

## Przykładowy format danych wejściowych

Plik `sample_input.json`:

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
  "baggage": [
    {
      "owner": "osoba_1",
      "pieces": 1,
      "height_cm": 55,
      "width_cm": 40,
      "depth_cm": 20,
      "weight_kg": 8
    }
  ],
  "interests": ["historia", "sztuka", "street-food"],
  "constraints": ["wegetariańskie opcje"],
  "accommodation_area": "Trastevere"
}
```

## Uwaga

Jeśli plan zawiera muzea lub miejsca o niepewnych godzinach działania, aplikacja dodaje sekcję ostrzeżeń z informacją: **"Sprawdź godziny otwarcia"**.

