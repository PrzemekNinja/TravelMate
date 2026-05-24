# Użycie TravelMate AI

## Wymagania

- Python 3.11+
- Klucz OpenAI API

## Konfiguracja

1. Wybierz providera modeli w `.env`:

  - `MODEL_PROVIDER=openai | anthropic | google | lmstudio`
  - `MODEL_TEMPERATURE=0.3` (opcjonalnie)

2. Uzupełnij wymagane dane dla wybranego providera:

  - OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`
  - Anthropic: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
  - Google: `GOOGLE_API_KEY`, `GOOGLE_MODEL`
  - LM Studio: `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL`, `LMSTUDIO_API_KEY` (domyślnie `lm-studio`)

3. (Opcjonalnie) Włącz integrację mapową HERE Technology API:

  - `HERE_API_KEY`
  - `HERE_BASE_URL` (domyślnie `https://geocode.search.hereapi.com/v1`)

4. Zainstaluj zależności z `requirements.txt`.

## Uruchomienie

Uruchom generator planu, przekazując plik wejściowy JSON:

`python -m travelmate.cli --input sample_input.json`

Wynik pojawi się jako Markdown w standardowym wyjściu terminala.

Uruchomienie GUI webowego Tailwind (przeglądarka):

`python -m travelmate.api.main`

Następnie otwórz `http://127.0.0.1:8000`.

## Parametry wejściowe

Model wejściowy `ItineraryInput`:

- `destination` (`str`, min. 2 znaki)
- `days` (`int`, 1–14)
- `budget` (`Low | Mid | Luxury`)
- `pace` (`Relaxed | Moderate | Intense`)
- `home_location` (`str | null`)
- `travel_start_date` (`YYYY-MM-DD | null`)
- `travel_end_date` (`YYYY-MM-DD | null`, nie wcześniejsza niż `travel_start_date`)
- `participants` (`int`, 1–30)
- `baggage` (`list[object]`, element: `owner`, `pieces`, `height_cm`, `width_cm`, `depth_cm`, `weight_kg`)
- `interests` (`list[str]`)
- `constraints` (`list[str]`)
- `accommodation_area` (`str | null`)

Przykład:

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

## Format wyjściowy

Aplikacja zwraca Markdown zawierający:

- nagłówek planu (`## 🗺️ Miasto - Plan Podróży (X Dni)`),
- sekcje dzienne z aktywnościami i posiłkami,
- podsumowanie transportu i kosztów,
- sekcję ostrzeżeń weryfikacyjnych (jeśli występują).

Wewnętrzny wynik warstwy geograficznej (`geo_output`) po włączeniu HERE zawiera dla każdego miejsca dnia:

- `name`
- `coordinates`: `lat`, `lng`
- `address`: `country`, `city`, `postcode`, `street`, `building_number`
- `website`
- `source` (`here` lub `unresolved`)

## Typowe problemy

### `Brak poprawnego OPENAI_API_KEY`

Uzupełnij odpowiedni klucz dla wybranego `MODEL_PROVIDER` i uruchom ponownie.

### `ModuleNotFoundError` dla zależności

Upewnij się, że uruchamiasz aplikację w tym samym środowisku Python, w którym instalowane były pakiety (najczęściej lokalne `.venv`).

### Ostrzeżenia dot. godzin otwarcia

To oczekiwane zachowanie `verification_agent` — model sygnalizuje miejsca wymagające ręcznego potwierdzenia.

### Brak pełnych danych miejsca z HERE

Jeśli HERE nie zwróci jednoznacznego wyniku, pole `source` dla miejsca może mieć wartość `unresolved`, a szczegóły adresu/website mogą być puste.
