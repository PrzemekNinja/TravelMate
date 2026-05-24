# TravelMate AI – Instrukcja uruchomienia interfejsu PWA

Poniżej opisano kroki potrzebne do lokalnego uruchomienia nowego interfejsu webowego (FastAPI + Chat UI + PWA) dla systemu wieloagentowego TravelMate AI.

---

## Wymagania wstępne

| Wymaganie | Minimalna wersja |
|-----------|-----------------|
| Python | 3.11+ |
| pip | 23+ (zalecane) |
| Klucz API wybranego providera LLM | — |
| (Opcjonalnie) Klucz HERE Maps | — |
| (Opcjonalnie) Klucz TripAdvisor | — |

---

## 1. Sklonuj lub pobierz projekt

```bash
git clone <url-repozytorium>
cd TravelMate
```

---

## 2. Utwórz i aktywuj środowisko wirtualne

```bash
# Utwórz środowisko
python -m venv .venv

# Aktywuj (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Aktywuj (Windows CMD)
.\.venv\Scripts\activate.bat

# Aktywuj (Linux / macOS)
source .venv/bin/activate
```

---

## 3. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

`requirements.txt` zawiera m.in.: `fastapi`, `uvicorn[standard]`, `langgraph`, `langchain-openai`, `pydantic`.

---

## 4. Skonfiguruj zmienne środowiskowe (`.env`)

Skopiuj plik przykładowy i uzupełnij wartości:

```bash
cp .env.example .env   # jeśli plik istnieje
# lub utwórz .env ręcznie
```

Minimalna zawartość `.env`:

```dotenv
# Wybierz providera: openai | anthropic | google | lmstudio
MODEL_PROVIDER=openai

# Klucz API wybranego providera
OPENAI_API_KEY=sk-...

# Opcjonalnie – HERE Maps (geokodowanie + POI)
HERE_API_KEY=...
HERE_GEOCODE_BASE_URL=https://geocode.search.hereapi.com/v1
HERE_SEARCH_BASE_URL=https://discover.search.hereapi.com/v1

# Opcjonalnie – TripAdvisor (zdjęcia, oceny)
TRIPADVISOR_API_KEY=...
```

> **Uwaga:** bez klucza HERE aplikacja nadal działa, ale nie wzbogaci planów o dane geolokalizacyjne.

---

## 5. Uruchom backend FastAPI (nowy interfejs PWA)

```bash
python -m travelmate.api.main
```

Serwer startuje pod adresem `http://127.0.0.1:8000`.

---

## 6. Otwórz aplikację w przeglądarce

```
http://127.0.0.1:8000
```

### PWA – instalacja na urządzeniu

Nowoczesne przeglądarki (Chrome, Edge, Safari na iOS) pozwolą zainstalować aplikację jako desktopową lub mobilną PWA. Kliknij ikonę instalacji w pasku adresu lub w menu przeglądarki → _Zainstaluj aplikację_.

---

## 7. Korzystanie z interfejsu

### Chat UI

- Wpisz opis wymarzonej podróży w polu tekstowym (np. _„5 dni w Tokio, budżet Mid, pour deux, zainteresowania: kultura i street food"_).
- Kliknij **Wyślij** – system uruchomi pipeline 6 agentów.
- Odpowiedź agentów oraz ścieżka do wygenerowanego planu HTML pojawią się w wątku rozmowy.

### Admin_View

- Kliknij przycisk **Admin_View** w prawym górnym rogu, żeby otworzyć panel debugowania.
- Panel wyświetla w czasie rzeczywistym:
  - **Agenci** – lista 6 agentów z aktualnym statusem (`IDLE`, `PROCESSING`, `DONE`, `ERROR`).
  - **Log stream** – surowy strumień logów z namespace `travelmate`.
  - **Debug JSON** – rozwijalne snapshoty danych po każdym etapie (`parsed_request`, `pipeline_result`, `saved_output`).

---

## 8. Wyniki planowania

Każdy wygenerowany plan jest automatycznie zapisywany w katalogu `output/` jako:

```
output/<timestamp>_<destynacja>_<dni>d/
├── itinerary.html   # interaktywna mapa + plan (Leaflet.js)
├── itinerary.md     # markdown z planem
└── request.json     # parametry wejściowe
```

Link do pliku HTML pojawi się w oknie czatu po zakończeniu generowania.

---

## Inne tryby uruchomienia

| Tryb | Komenda |
|------|---------|
| **Nowy interfejs PWA (FastAPI)** | `python -m travelmate.api.main` |
| **CLI (JSON wejscie)** | `python -m travelmate.cli --input sample_input.json` |
| **Windows (1 klik, PWA)** | `run_gui.bat` |

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|-------------|
| `Import "fastapi" could not be resolved` | Zainstaluj zależności: `pip install -r requirements.txt` |
| Port 8000 zajęty | Zmień port: `uvicorn travelmate.api.main:app --port 8001` |
| Brak planu w odpowiedzi | Sprawdź klucz API w `.env` i logi w `Admin_View` |
| Ostrzeżenie o Pydantic V1 | Znane ograniczenie `langchain_core` na Python ≥ 3.14; nie wpływa na działanie |
| Service worker nie rejestruje się | Upewnij się, że serwer działa na `localhost` (HTTPS nie jest wymagany lokalnie) |
