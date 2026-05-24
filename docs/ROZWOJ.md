# Rozwój i utrzymanie

## Struktura katalogów

- `travelmate/models.py` – kontrakty danych.
- `travelmate/prompts/` – prompty i reguły domenowe per agent.
- `travelmate/graph.py` – orkiestracja agentów i rendering odpowiedzi.
- `travelmate/cli.py` – warstwa uruchomieniowa.
- `docs/` – dokumentacja projektowa i operacyjna.

## Jak dodać nowego agenta

1. Dodaj prompt w nowym pliku w `travelmate/prompts/`.
2. Dodaj model wyjściowy w `travelmate/models.py` (jeśli potrzebny).
3. Zaimplementuj funkcję agenta w `travelmate/graph.py`.
4. Rozszerz `PlannerState` o nowe pole stanu.
5. Dodaj węzeł i krawędzie w `build_graph()`.
6. Zaktualizuj `formatter_agent`, jeśli nowy agent wpływa na finalny output.

## Dobre praktyki

- Utrzymuj prompty krótkie i jednoznaczne.
- Korzystaj ze strukturalnych wyjść (`with_structured_output`) tam, gdzie to możliwe.
- Traktuj `formatter_agent` jako jedyne miejsce odpowiedzialne za finalny Markdown.
- Nie mieszaj logiki walidacji wejścia z logiką formatowania.
- Konfigurację modeli utrzymuj wyłącznie w `travelmate/tools/config.py` i `travelmate/tools/model_factory.py`.
- Integracje mapowe (HERE) utrzymuj w `travelmate/tools/here_maps.py`, a nie bezpośrednio w promptach/agentach.

## Testowanie

Minimalny zestaw kontroli przed release:

1. Walidacja składni plików Python.
2. Smoke test CLI na `sample_input.json`.
3. Test scenariusza bez klucza API (powinien zwrócić czytelny błąd).
4. Test scenariusza z kluczem API (powinien zwrócić kompletny Markdown).
5. Test enrichmentu HERE (`get_here_places_details`) — sprawdź obecność `coordinates`, `address.*`, `website`.

## Ograniczenia obecnej wersji

- Brak persystencji historii planów.
- Brak API HTTP (obecnie wyłącznie CLI).
- Brak testów automatycznych (`pytest`) w repozytorium.
- Część miejsc może wracać jako `source="unresolved"`, jeśli HERE nie zwróci jednoznacznego dopasowania.

## Kierunki rozbudowy

- Dodanie warstwy API (np. FastAPI).
- Dodanie testów jednostkowych i integracyjnych.
- Caching odpowiedzi modelu dla podobnych zapytań.
- Integracja z realnymi danymi POI / mapami / godzinami otwarcia.
