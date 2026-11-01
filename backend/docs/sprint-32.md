# Sprint 32 — zaakceptowane korekty istniejących treningów

W zakładce **Trener**, po otwarciu dostępu prywatnym kodem, panel „Korekta
istniejącego treningu” pobiera świeży plan z Google Sheets. Wybór dotyczy
konkretnego fizycznego wiersza, także gdy jednego dnia są dwie jednostki.
Dostępne są gotowe, edytowalne warianty: spokojny bieg z 70% dotychczasowej
objętości albo odpoczynek oraz własny przebieg treningu. Zawodnik podaje
uzasadnienie, ogląda trwały podgląd przed/po i osobno akceptuje zapis lub odrzuca
propozycję. Gotowe warianty są szablonami; nie stanowią nowej oceny regeneracji.
Czat może omówić korektę, ale sam nie zapisuje planu.

Zmiana obejmuje tytuł, dystans, czas i opis. Nie zmienia daty, priorytetu ani
pozostałych kolumn. Opis zachowuje dokładną wcześniejszą treść, wszystkie uwagi
oraz wcześniejsze korekty, po czym dopisuje obowiązujący przebieg i końcową notkę:

> PaceMind 2026-11-01 | Zmiana: tytuł, dystans, czas, opis treningu. Uzasadnienie: zmęczenie po ostatnich sesjach.

Data notki jest datą przygotowania zaakceptowanego podglądu, w strefie
Europe/Warsaw. Parser typu i struktury treningu korzysta z ostatniego
obowiązującego przebiegu, nie ze starych interwałów ani uzasadnienia.
Oryginał, wynik, uzasadnienie, czas przygotowania i stan decyzji są zapisane
w trwałej bazie w `plan_corrections`. Interfejs pokazuje ostatnich 100 korekt;
starsze pozostają w bazie. Podgląd można ponownie otworzyć z historii po
odświeżeniu strony. Odrzucenie niczego nie zmienia w arkuszu.

## API

Wspólna autoryzacja z czatem: `Authorization: Bearer <COACH_CHAT_ACCESS_CODE>`.
Brak konfiguracji wyłącza endpointy; błędy dostawcy nie ujawniają szczegółów.

- `GET /coach/corrections/plan`: aktualna wersja i nadchodzące wiersze.
- `GET /coach/corrections`: historia wraz z pełnym przed/po.
- `POST /coach/corrections/preview`: UUID `id`, wersja `version`, fizyczny `row`,
  `change` z tytułem, opisem, dystansem i czasem oraz `reason`.
- `POST /coach/corrections/{UUID}/decision`: `decision: accept` albo `reject`.

Akceptacja przesyła tylko ID i decyzję. Zapisuje dokładnie podgląd z serwera.
Powtórzenie UUID z inną treścią daje 409. Ponowienie zakończonej decyzji zwraca
wcześniejszy wynik; sprzeczna decyzja daje 409. Daty minione są blokowane.
Wersja obejmuje źródło, nagłówki, kolejność i pełną treść wierszy, także
pozostałe uwagi. Zmiana w arkuszu po podglądzie wymusza nowy podgląd.
Zapis zmienionych komórek używa jednego `batch_update` i trybu `RAW`.

## Współbieżność i niepewny wynik

`plan_write_gate` jest wspólną trwałą blokadą wszystkich instancji backendu.
Atomowe przejście `preview → writing` poprzedza sprawdzenie aktualności i zapis.
Po zapisie backend odczytuje arkusz i potwierdza pełną zgodność z podglądem.
Utrata odpowiedzi po udanym zapisie nie powoduje drugiego zapisu. Po błędzie
bez potwierdzenia stan `writing` i blokada pozostają także po restarcie; ponowienie
tej samej akceptacji tylko sprawdza arkusz. Inne zapisy pozostają zablokowane.

Jeżeli zapis na pewno nie nastąpił lub ktoś zmienił wiersz przed potwierdzeniem,
administrator musi porównać zapisany przed/po z rzeczywistym arkuszem. Po
rozstrzygnięciu może transakcyjnie oznaczyć korektę jako `stale` i zwolnić
`plan_write_gate.owner` wyłącznie dla tego ID. Nie wolno zwalniać blokady, gdy
poprzedni proces nadal może wysłać zapis. Automatyczne odtwarzanie niepewnych
operacji celowo nie jest wykonywane.

Google Sheets nie udostępnia atomowego compare-and-swap dla komórek. Odczyt
bezpośrednio przed zapisem wykrywa zmiany od podglądu, lecz nie gwarantuje
wykrycia ręcznej edycji dokonanej pomiędzy tym odczytem a aktualizacją. Podczas
akceptowania korekty należy unikać równoczesnej ręcznej edycji tego treningu.
Blokada zabezpiecza wszystkie zapisy PaceMind korzystające z tej samej bazy.

## Wdrożenie i weryfikacja

`Base.metadata.create_all` tworzy dwie nowe tabele bez zmiany istniejących.
Zachować trwałą bazę Cloud SQL oraz dotychczasowe ustawienia Google Sheets.
Konto Google używane przez backend musi mieć **prawo edycji** arkusza. Kod
nie wymaga nowych sekretów. Wdrożyć backend przed frontendem.

- Backend: `cd backend && .venv/bin/python -m pytest tests -q` — **261 passed**.
- Chromium: `cd tests/frontend && npm test` — **19 passed**.

Nowe testy obejmują autoryzację, walidację, zachowanie uwag i oryginału,
idempotencję, sprzeczną decyzję, nieaktualny plan, minioną datę, blokadę
nakładających się zapisów, restart po niepewnym wyniku, utratę odpowiedzi po
zapisie, tryb RAW i klasyfikację nowej jednostki z zachowaną historią.
Przeglądarka sprawdza podgląd, akceptację, ponowne otwarcie historii, tekst
zawierający HTML i szerokość telefonu. Zewnętrzne Google Sheets i płatny model
nie są wywoływane w testach. Produkcyjnych uprawnień zapisu nie sprawdzano.

Sprint 32A — pełny plan pod kalendarz startów — pozostaje poza zakresem.
