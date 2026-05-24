# Dokumentacja biznesowa — TravelMate AI

## 1. Cel biznesowy

TravelMate AI to aplikacja wspierająca planowanie podróży poprzez automatyczne generowanie planu dzień-po-dniu na podstawie opisu użytkownika. 

Główna wartość biznesowa:

- skrócenie czasu przygotowania planu podróży,
- standaryzacja jakości planów,
- poprawa doświadczenia użytkownika dzięki prostemu wejściu w języku naturalnym,
- możliwość szybkiej adaptacji do różnych dostawców modeli AI.

## 2. Problem, który rozwiązujemy

Użytkownicy często:

- nie wiedzą, od czego zacząć planowanie,
- mają ograniczony czas na research,
- otrzymują niespójne rekomendacje z wielu źródeł,
- potrzebują planu uwzględniającego budżet, tempo i ograniczenia.

TravelMate AI agreguje te potrzeby do jednego, uporządkowanego procesu.

## 3. Grupy docelowe

### 3.1 Użytkownicy indywidualni

- pary i rodziny planujące city-break lub dłuższy wyjazd,
- osoby podróżujące samodzielnie,
- użytkownicy preferujący szybki, gotowy plan zamiast ręcznego researchu.

### 3.2 B2B / partnerzy (potencjał)

- biura podróży i konsultanci travel,
- portale contentowe o podróżach,
- firmy benefitowe oferujące narzędzia planowania wyjazdów.

## 4. Propozycja wartości (Value Proposition)

- **Szybkość**: plan w kilka minut.
- **Spójność**: sekwencja agentów pilnuje logiki i jakości wyniku.
- **Personalizacja**: uwzględnienie preferencji, ograniczeń i stylu podróżowania.
- **Czytelność**: gotowy output w formacie Markdown/HTML.
- **Elastyczność technologiczna**: obsługa wielu providerów LLM (OpenAI, Anthropic, Google, LM Studio).

## 5. Zakres produktu (MVP)

W zakresie obecnej wersji:

- wejście użytkownika w języku naturalnym,
- parser strukturyzujący wymagania,
- pipeline agentów generujących plan podróży,
- walidacja i ostrzeżenia (np. godziny otwarcia),
- zapis wyników do katalogu `output/`,
- nowy interfejs GUI webowy (Tailwind + FastAPI + PWA).

Poza zakresem MVP:

- system rezerwacji,
- płatności,
- personalizowane konta użytkowników,
- zewnętrzne API z autoryzacją i billingiem.

## 6. Kluczowe procesy biznesowe

1. Użytkownik wprowadza potrzeby podróży.
2. System parsuje dane i buduje profil podróży.
3. System generuje draft planu i weryfikuje ryzyka.
4. Użytkownik otrzymuje finalny plan oraz pliki wynikowe.

## 7. KPI i metryki sukcesu

### 7.1 Produktowe

- współczynnik poprawnie ukończonych generacji,
- średni czas generacji planu,
- odsetek planów wymagających ponownego uruchomienia,
- wykorzystanie opcji „testowej wycieczki” (diagnostyka UX).

### 7.2 Jakościowe

- satysfakcja użytkownika (NPS/CSAT),
- ocena przydatności planu,
- czytelność i kompletność wyników.

### 7.3 Operacyjne

- liczba błędów krytycznych na 100 uruchomień,
- dostępność dostawcy modelu AI,
- koszt generacji per plan.

## 8. Ryzyka biznesowe i ograniczenia

- zależność od zewnętrznych modeli AI i ich dostępności,
- zmienność kosztów API,
- ryzyko halucynacji modelu (ograniczane przez etap weryfikacji),
- brak integracji z rzeczywistymi systemami rezerwacji.

## 9. Model rozwoju produktu (roadmapa)

### Etap 1 — Stabilizacja MVP

- poprawa jakości parsera wejścia,
- lepsza obserwowalność procesu (czytelne logi kroków),
- standaryzacja komunikatów błędów.

### Etap 2 — Użyteczność i retencja

- profile użytkowników,
- biblioteka gotowych scenariuszy podróży,
- zapis i porównywanie wersji planu.

### Etap 3 — Monetyzacja i B2B

- API dla partnerów,
- rozliczanie per generacja/per użytkownik,
- rozszerzenia premium (np. integracja z mapami i POI).

## 10. Interesariusze

- **Product Owner**: priorytety i backlog.
- **Zespół inżynierski**: rozwój, utrzymanie, jakość.
- **Użytkownicy końcowi**: feedback, walidacja wartości.
- **Partnerzy technologiczni (LLM providers)**: dostępność i SLA modeli.

## 11. Definicja gotowości biznesowej (Business DoD)

Nowa funkcjonalność uznawana jest za gotową, gdy:

- ma opis wartości i wpływu na KPI,
- ma scenariusz użycia i kryteria akceptacji,
- jest opisana w dokumentacji użytkowej i biznesowej,
- posiada plan monitorowania po wdrożeniu.
