# Architektura TravelMate AI

## Cel systemu

TravelMate AI generuje plan podróży dzień-po-dniu na bazie preferencji użytkownika, z naciskiem na:

- spójność geograficzną (Geo-Clustering),
- realne tempo zwiedzania,
- dopasowanie gastronomii do lokalizacji, budżetu i ograniczeń.

## Główne komponenty

### `travelmate/models.py`

Zawiera modele danych Pydantic oraz stan grafu:

- `ItineraryInput` – wejście użytkownika,
- `GeoOutput` – podział na miejsca i strategia przemieszczania,
- `ItineraryDraft` – strukturalny plan dzienny,
- `VerificationOutput` – ostrzeżenia i korekty,
- `PlannerState` – wspólny stan przepływający przez węzły LangGraph.

W warstwie geo dostępne są też pomocnicze modele draftu (`GeoOutputDraft`), które są wzbogacane danymi HERE przed zwróceniem finalnego `GeoOutput`.

### `travelmate/prompts/`

Definiuje prompty w osobnych plikach per agent:

- `profile_prompt.py`
- `transport_prompt.py`
- `geo_prompt.py`
- `itinerary_prompt.py`
- `verification_prompt.py`
- `formatter_prompt.py`

### `travelmate/agents/`

Każdy agent ma osobny plik:

- `profile_agent.py`
- `transport_agent.py`
- `geo_agent.py`
- `itinerary_agent.py`
- `verification_agent.py`
- `formatter_agent.py`

### `travelmate/tools/`

Narzędzia współdzielone:

- `config.py` – wczytanie konfiguracji providerów,
- `model_factory.py` – switch modeli (OpenAI / Anthropic / Google / LM Studio),
- `here_maps.py` – integracja HERE (geocode/discover/lookup) i normalizacja szczegółów miejsc,
- `payload.py` – serializacja wejścia,
- `markdown_formatter.py` – budowa finalnego Markdown.

### `travelmate/graph.py`

Zawiera:

- wiring agentów,
- definicję grafu (`build_graph`).

### `travelmate/cli.py`

CLI odpowiedzialne za:

- wczytanie wejścia JSON,
- uruchomienie grafu,
- wypisanie finalnego Markdown.

## Przepływ danych (LangGraph)

Sekwencja węzłów:

`START -> profile_agent -> transport_agent -> geo_agent -> itinerary_agent -> verification_agent -> formatter_agent -> END`

### 1) `profile_agent`

Buduje skrót profilu podróżnika (styl, tempo, budżet, główne zainteresowania).

### 2) `transport_agent`

Na bazie destynacji + profilu użytkownika + danych wejściowych (dom, daty, uczestnicy, bagaż) generuje raport transportowy markdown dla wariantów:

- loty,
- kolej,
- wynajem auta,
- auto własne.

### 3) `geo_agent`

Tworzy draft podziału planu na konkretne miejsca dla każdego dnia, a następnie wzbogaca każde miejsce przez HERE API.

Finalne `GeoOutput` zawiera dla `morning_zone`, `afternoon_zone`, `evening_zone`:

- `name`,
- `coordinates` (`lat`, `lng`),
- `address` (`country`, `city`, `postcode`, `street`, `building_number`),
- `website`,
- `source` (`here` lub `unresolved` przy fallbacku).

### 4) `itinerary_agent`

Na bazie wejścia + profilu + geo-planu generuje właściwy harmonogram (atrakcje, lunch, kolacja) w formacie `ItineraryDraft`.

### 5) `verification_agent`

Weryfikuje potencjalne ryzyka dostępności (np. dni zamknięcia muzeów) i zwraca ostrzeżenia/korekty jako `VerificationOutput`.

### 6) `formatter_agent`

Konwertuje dane strukturalne do finalnego Markdown zgodnego z docelowym szablonem odpowiedzi.

## Zarządzanie konfiguracją

`model_factory.get_chat_model()` korzysta z:

- `MODEL_PROVIDER` (`openai`, `anthropic`, `google`, `lmstudio`),
- odpowiednich zmiennych modelu/klucza per provider,
- `MODEL_TEMPERATURE`.

Integracja mapowa korzysta dodatkowo z:

- `HERE_API_KEY`,
- `HERE_BASE_URL` (domyślnie `https://geocode.search.hereapi.com/v1`).

Brak poprawnego klucza dla aktywnego providera powoduje kontrolowany wyjątek `ModelConfigurationError`.

## Decyzje projektowe

- **Strukturalne wyjścia agentów** (`with_structured_output`) redukują ryzyko niespójnego JSON.
- **Sekwencyjny graf** upraszcza debugowanie i jest wystarczający dla liniowego procesu planowania.
- **Oddzielny formatter** rozdziela logikę planowania od prezentacji.
