# Dokumentacja techniczna — TravelMate AI

## 1. Przegląd systemu

TravelMate AI to aplikacja Python wykorzystująca sekwencyjny workflow agentowy oparty o LangGraph. 

Tryby uruchomienia:

- CLI: `python -m travelmate.cli --input sample_input.json`
- GUI webowe (Tailwind + FastAPI): `python -m travelmate.api.main`

## 2. Architektura logiczna

### 2.1 Warstwy

- `travelmate/web/` — frontend interfejsu użytkownika (Tailwind + PWA).
- `travelmate/api/` — backend interfejsu użytkownika (FastAPI + WebSocket).
- `travelmate/services/` — logika aplikacyjna (orchestracja parse → plan → zapis).
- `travelmate/agents/` — moduły odpowiedzialne za kolejne etapy planowania.
- `travelmate/prompts/` — prompty systemowe i zadaniowe per agent.
- `travelmate/tools/` — narzędzia wspólne (config, model factory, parser, logging).
- `travelmate/models.py` — kontrakty danych i typy stanu.

### 2.2 Graf przetwarzania (LangGraph)

Sekwencja:

`START -> profile_agent -> geo_agent -> itinerary_agent -> verification_agent -> formatter_agent -> END`

## 3. Komponenty i odpowiedzialności

### 3.1 `PlannerService` (`travelmate/services/planner_service.py`)

- wejście: tekst użytkownika,
- wykonanie parsowania wejścia,
- uruchomienie grafu agentów,
- zapis wyników (`output/*`),
- zwrot obiektu `PlannerRunResult`.

### 3.2 Parser wejścia (`travelmate/tools/input_parser.py`)

Obsługiwane formaty:

1. JSON,
2. `key: value`,
3. język naturalny (NLP parser via LLM).

Parser zawiera:

- heurystykę wykrywania formatu,
- fallback do NLP parsera,
- domyślne wartości (`days=3`, `budget=Mid`, `pace=Moderate`) i listę założeń.

### 3.3 Agenci

- `profile_agent` — profil podróżnika,
- `geo_agent` — strategia geograficzna i podział dni, wzbogacony danymi HERE per miejsce,
- `itinerary_agent` — draft planu (aktywności + posiłki),
- `verification_agent` — ostrzeżenia i poprawki,
- `formatter_agent` — finalny markdown.

Każdy agent używa strukturalnego outputu (`with_structured_output`) tam, gdzie to potrzebne.

`geo_agent` działa dwuetapowo:

1. LLM tworzy `GeoOutputDraft` (nazwy miejsc),
2. warstwa HERE (`travelmate/tools/here_maps.py`) rozwiązuje szczegóły każdego miejsca i buduje finalny `GeoOutput`.

### 3.4 Model factory (`travelmate/tools/model_factory.py`)

Obsługiwani providerzy:

- OpenAI,
- Anthropic,
- Google,
- LM Studio.

`get_model_runtime_status()` zwraca: provider, model, flagę aktywności i diagnostykę.

## 4. Modele danych

Kluczowe kontrakty (`travelmate/models.py`):

- `ItineraryInput` — wejście biznesowe,
- `GeoOutput` — wynik warstwy geograficznej,
- `GeoPlace`/`GeoAddress`/`GeoCoordinates` — szczegóły miejsca (adres i współrzędne),
- `ItineraryDraft` — strukturalny plan,
- `VerificationOutput` — ostrzeżenia i korekty,
- `PlannerState` — stan przekazywany między węzłami.

### 4.1 Struktura GeoOutput (po enrichment HERE)

Dla każdego dnia pola `morning_zone`, `afternoon_zone`, `evening_zone` mają strukturę:

- `name`
- `coordinates.lat`, `coordinates.lng`
- `address.country`, `address.city`, `address.postcode`, `address.street`, `address.building_number`
- `website`
- `source` (`here` albo `unresolved`)

## 5. Logowanie i obserwowalność

### 5.1 Namespace i format

Logi aplikacyjne są emitowane w namespace `travelmate.*`.

Format prezentacji:

`[agent_name] YYYY-MM-DD HH:MM:SS LEVEL: komunikat`

### 5.2 Zasady

- logujemy kroki i wyniki (outputy),
- nie logujemy pełnych promptów/payloadów,
- UI wyświetla tylko logi aplikacyjne (bez szumu z bibliotek).

## 6. Interfejs użytkownika

### 6.1 Web (Tailwind + FastAPI + PWA)

Pliki: `travelmate/web/index.html`, `travelmate/api/main.py`

Funkcje:

- chatowy interfejs planowania,
- status agentów (`IDLE`/`PROCESSING`/`DONE`/`ERROR`) aktualizowany w czasie rzeczywistym,
- panel `Admin_View` z logami i eventami debug,
- PWA (manifest + service worker),
- generacja i linkowanie do artefaktów `output/*/itinerary.html`.

## 7. Konfiguracja środowiska

Źródło: `.env` + `travelmate/tools/config.py`

Kluczowe zmienne:

- `MODEL_PROVIDER` = `openai|anthropic|google|lmstudio`
- `MODEL_TEMPERATURE`
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- `GOOGLE_API_KEY`, `GOOGLE_MODEL`
- `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL`, `LMSTUDIO_API_KEY`
- `HERE_API_KEY`, `HERE_BASE_URL`

## 8. Artefakty wyjściowe

Każde uruchomienie zapisuje:

- `itinerary.html`
- `itinerary.md`
- `request.json`

w dedykowanym katalogu w `output/`.

## 9. Obsługa błędów

- Brak/niepoprawny klucz API -> `ModelConfigurationError`.
- Niepoprawne wejście użytkownika -> `ValueError` z komunikatem użytkowym.
- Błędy wykonania pipeline -> logowane w UI + komunikat dla użytkownika.

Dla HERE:

- brak klucza `HERE_API_KEY` lub błąd sieci nie przerywa pipeline,
- `geo_agent` zwraca fallback `source="unresolved"` i puste pola szczegółowe dla nierozwiązanych miejsc.

## 10. Bezpieczeństwo i prywatność

- Sekrety trzymane wyłącznie w `.env` (nie commitować kluczy),
- brak trwałej persystencji danych użytkowników poza lokalnym `output/`,
- rekomendacja: dodać maskowanie danych wrażliwych w logach przy wdrożeniach produkcyjnych.

## 11. Operacje i utrzymanie

### 11.1 Minimalny smoke test po zmianach

1. `python -m travelmate.cli --input sample_input.json`
2. `python -m travelmate.api.main`
3. sprawdzenie logów i zapisu plików w `output/`.

### 11.2 Weryfikacja składni

`python -m compileall travelmate`

## 12. Proponowane rozszerzenia techniczne

- testy automatyczne (`pytest`) dla parsera i serwisu,
- testy integracyjne workflow agentów,
- warstwa API (FastAPI),
- cache wyników dla podobnych zapytań,
- integracja z realnymi źródłami danych POI i godzin otwarcia.
