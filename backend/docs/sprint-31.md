# Sprint 31 — Coach Chat i podział aplikacji

## Interfejs

Trzy widoki w istniejącej aplikacji, bez nowego frameworka:

- **Dzisiaj** (`#today`): regeneracja, plan, rekomendacja, ostatnie sesje i skrót tygodnia.
- **Tydzień** (`#week`): raport Weekly Coach Review i przegląd 28 dni.
- **Trener** (`#coach`): prywatny czat, historia rozmów i podpowiedzi pytań.

Na komputerze nawigacja jest nad treścią; na telefonie przy dolnej krawędzi.
Linki bezpośrednie, odświeżenie i przyciski wstecz/dalej przeglądarki zachowują widok.
Raport tygodnia i przegląd 28 dni nie są pobierane na starcie Dzisiaj.
Skrót Dzisiaj pokazuje nagłówek ostatnio otwartego raportu wraz z jego datami
(z pamięci bieżącej karty); przed pierwszą wizytą zawiera odnośnik do raportu.
Dotychczasowy zduplikowany blok Training Context zastępuje przegląd w Tygodniu.

Przy rekomendacji, treningu i wybranym tygodniu są wejścia do rozmowy. Otwierają
nowy wątek z pytaniem i wskazanym kontekstem; nie wysyłają pytania automatycznie.
Źródła i ograniczenia odpowiedzi są rozwijane pod jej treścią.
Tekst zawodnika, odpowiedź AI i źródła są wyświetlane jako tekst, bez wykonywania HTML.

## Dane i AI

`CoachChatContextService` odświeża dane przy każdym pytaniu. Wykorzystuje
CoachContextService, aktualny cel, oceny sesji i regeneracji z ostatnich 28 dni,
plan na następne 7 dni, a także wskazany tydzień lub trening. Pierwszy niepełny
tydzień w oknie nie przenosi do kontekstu agregatów z dni poza oknem.
Źródło planu jest pobierane raz dla raportów i wybranego treningu w obrębie odpowiedzi.
Częściowe awarie są jawnie opisywane; dostępny cel pozostaje niezależny od awarii
rekomendacji dnia. Brak źródeł blokuje płatne wywołanie.

AI otrzymuje świeży kontekst oraz ostatnie 8 zakończonych wymian. Nie oblicza
nowych wskaźników ani prognoz startowych i nie zmienia planu, celu, feedbacku lub
pamięci zawodnika. Odczucia z rozmowy nie stają się automatycznie trwałą pamięcią.
Używany jest istniejący klient OpenAI i konfiguracja `OPENAI_API_KEY`/`OPENAI_MODEL`.
Dla czatu: maksymalnie 2000 tokenów odpowiedzi, timeout 45 sekund i brak
automatycznych ponowień SDK.

## API i zapis

Wszystkie endpointy wymagają nagłówka `Authorization: Bearer <kod>`:

- `GET /coach/conversations` — ostatnich 30 rozmów.
- `POST /coach/conversations`, `{ "id": "UUID" }` — idempotentne utworzenie wątku.
- `GET /coach/conversations/{UUID}` — zakończone wymiany wraz ze źródłami i datą kontekstu.
- `POST /coach/chat` — pytanie, identyfikator wątku i żądania, wybrany kontekst.

Przykładowe ciało pytania:

```json
{
  "conversation_id": "UUID",
  "request_id": "UUID",
  "message": "Co dał ostatni tydzień?",
  "context": {"kind": "week", "week_start": "2026-10-19"}
}
```

Pozostałe konteksty: `{ "kind": "today" }` oraz
`{ "kind": "workout", "session_id": "...", "date": "YYYY-MM-DD" }`.
Pytanie ma od 1 do 2000 znaków po przycięciu białych znaków. Niedziela zamiast
poniedziałku, przyszły tydzień i trening bez daty są odrzucane.

Nowe tabele: `coach_conversations`, `coach_chat_turns`, `coach_chat_gate`.
Istniejący `Base.metadata.create_all` tworzy je przy starcie backendu; nie zmienia
istniejących tabel. Historia jest w dotychczasowej bazie, nie w localStorage.
Na Cloud Run należy zachować istniejące połączenie z trwałą bazą; lokalny SQLite
w kontenerze nie gwarantuje historii po wymianie instancji.

Powtórzenie tego samego request_id i treści zwraca zapisaną odpowiedź bez
kolejnego wywołania AI. Inna treść z tym samym ID daje 409. Nieudane pytanie można
ponowić z tym samym ID; błąd sieci po zapisaniu odpowiedzi nie tworzy drugiego wpisu.
Błędy dostawców nie ujawniają szczegółów połączeń ani danych uwierzytelnienia.

## Prywatny kod i limity

Wybrany wariant przeznaczony jest dla jednej osoby. Wszyscy posiadacze kodu mają
dostęp do tej samej historii i tych samych danych zawodnika. Nie jest to system
kont wielu zawodników. Kod nie chroni innych, wcześniej istniejących endpointów.

Backend wymaga `COACH_CHAT_ACCESS_CODE` o długości co najmniej 16 znaków;
zalecany jest losowy kod z co najmniej 32 bajtów losowości. Brak lub krótki kod
wyłącza endpointy czatu (503); błędny kod daje 401. Porównanie ma stały czas.
Kod jest wpisywany w zakładce Trener i przechowywany w sessionStorage tej karty,
nie w URL, localStorage ani repozytorium. „Zamknij dostęp” usuwa go z karty.

Baza utrzymuje wspólny limit dla wszystkich instancji: odstęp co najmniej 10 sekund,
60 rozpoczętych prób na dobę UTC i jedno aktywne generowanie naraz. Błędy AI także
zużywają próbę. Dzierżawa wygasa po 90 sekundach i jest odnawiana po zebraniu
kontekstu, przed wywołaniem AI. Opóźniona próba bez dzierżawy nie zaczyna generowania.
Zapisane odpowiedzi można odczytać ponownie bez zużycia limitu.

## Wdrożenie

1. W Google Secret Manager utworzyć sekret z prywatnym kodem. Wartości nie
   wpisywać do repozytorium ani czatu. Konto usługi Cloud Run musi mieć dostęp
   do tego sekretu.
2. W Cloud Run podpiąć sekret do zmiennej `COACH_CHAT_ACCESS_CODE`. Zachować
   istniejące zmienne bazy, Google Sheets i OpenAI.
3. Wdrożyć backend, a potem frontend:

```sh
gcloud run deploy pacemind-backend --source backend --region=europe-central2 --project=pacemind-503211
npx --yes firebase-tools deploy --only hosting --project=pacemind-503211
```

4. Sprawdzić Dzisiaj/Tydzień/Trener na komputerze i telefonie. Otworzyć rozmowę
   kodem, zadać pytanie o rzeczywiste dane, odświeżyć stronę i sprawdzić historię.
   Przy błędnym kodzie historia ma pozostać niedostępna.

Nowe pliki `app-navigation.js` i `coach-chat.js` są publikowane przez istniejącą
konfigurację Firebase Hosting. CSS, app.js i weekly-review.js mają nowe wersje URL.

## Weryfikacja lokalna

Z backend/: `.venv/bin/python -m pytest tests -q`.
Z tests/frontend/: `npm test` (Chromium i istniejące backend/.venv).
Testy AI używają kontrolowanej odpowiedzi zamiast płatnego połączenia; testy
przeglądarkowe korzystają z rzeczywistych lokalnych endpointów, kodu dostępu,
SQLite i mechanizmu ponowień. Żądania produkcyjnego hosta są przechwytywane lokalnie.
Walidacja na produkcji i odpowiedzi rzeczywistego modelu wymagają osobnego wdrożenia.

Weryfikacja końcowa: **247 testów backendu i 18 testów Chromium przeszło**.
Sprawdzono także wizualnie układ komputera i telefonu. Produkcyjne połączenie
z OpenAI, uprawnienia Secret Manager i trwałość na produkcyjnej bazie nie były
w tym środowisku sprawdzane. Testy zapisu i współdzielonej bramki używają SQLite.
