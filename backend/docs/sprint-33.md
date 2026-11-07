# Sprint 33 — wspólna pamięć zawodnika i aktualny cel

W zakładce **Trener → Co PaceMind o mnie wie** zawodnik widzi potwierdzony cel,
cykl 10-dniowy, pamięć, propozycje do zatwierdzenia i historię. Nie ma formularza
budżetu czasu ani narzuconych dni tygodnia. Zakładki Google Sheets pozostają
bez zmian: `plan_import` oraz `race_calendar` z dotychczasowymi kolumnami.

## Cel i cykl

Cel wybiera się spośród przyszłych startów A z `race_calendar`. Najpierw jest
podgląd dotychczasowego i proponowanego celu; dopiero potwierdzenie zapisuje
wybór do trwałej bazy. Odczyt i potwierdzenie sprawdzają aktualność kalendarza.
Ten proces nie modyfikuje Google Sheets ani priorytetów innych zawodów.

`CurrentGoalService` jest wspólnym źródłem potwierdzonego celu. Korzystają z niego
kontekst czatu, wyjaśnienia AI, postęp celu, raport tygodniowy i produkcyjne
endpointy celu. Planowanie odczytuje ten sam wybór w profilu i wymaga, żeby
pozostał zgodny z kalendarzem oraz mieścił się w zakresie planu. Nie wybiera
innego A tylko dlatego, że jest wcześniejszy. Po zakończeniu celu trzeba
potwierdzić następny; nie ma automatycznej zmiany celu.

Usunięto dotychczasowy cel wpisany na sztywno. Bez potwierdzenia cel jest
`unconfigured`, postęp do celu ma niewystarczające dane, a generator prosi o wybór
w profilu. Nie ma cichego przejęcia dawnych dat i czasów z kodu.

Cykl ma zawsze 10 dni. Zawodnik może potwierdzić datę dnia 1 albo pozostawić
początek nieustalony. Dzień cyklu wynika z tej daty, a planowanie respektuje
przesunięcie również przy rozpoczęciu planu w środku cyklu. Potwierdzona data
ma pierwszeństwo przed propozycją modelu; nie ma resetu w poniedziałek.

## Pamięć i propozycje z rozmów

Rodzaje ustaleń: treningowe, kontuzja, ograniczenie, reakcja na obciążenie i inne.
Każda nowa wersja ma treść, stan (`current`, `historical`, `resolved`), datę
zgłoszenia, datę potwierdzenia oraz źródło. Starsze wpisy bez tych metadanych
są oznaczone `unreviewed`, bez automatycznego uznania ich za aktualną kontuzję
lub potwierdzone ustąpienie problemu.

Czat może zaproponować najwyżej jedno ustalenie z bieżącej wiadomości zawodnika.
Odpowiedź modelu ma format JSON z `answer` i `suggestions`; wcześniejsze zwykłe
odpowiedzi tekstowe pozostają obsługiwane. Sugestia wymaga dokładnego cytatu
z wiadomości zawodnika. Cytat z odpowiedzi AI, diagnoza dopisana przez model lub
niezgodne źródło nie mogą automatycznie stać się pamięcią. Szkic z nieaktualnego
profilu jest pomijany z informacją o ograniczeniu; odpowiedź czatu pozostaje.

Pod odpowiedzią pojawia się „Zapamiętać to ustalenie?” i przycisk podglądu.
Dodatkowo przy każdej wiadomości zawodnika jest ręczne wejście do przygotowania
ustalenia. Samo wysłanie pytania nie zapisuje pamięci. Zawodnik ogląda przed/po,
źródłowy cytat i osobno wybiera **Zapamiętaj** albo odrzucenie.

Poprawienie lub oznaczenie ustąpienia tworzy nowy rekord pamięci i dezaktywuje
poprzednią wersję. Oryginał, stan i cytat pozostają w historii, a nowa wersja
wskazuje poprzednią. `resolved` oznacza potwierdzone zgłoszenie zawodnika,
nie medyczną ocenę modelu. Zapisane reakcje na trening zachowują źródło;
propozycje AI same nie dowodzą skuteczności treningu.

## Wspólne dane i bezpieczeństwo zapisu

Istniejący `AthleteMemoryService` zwraca teraz metadane stanu, źródła i daty.
Profil trafia do kontekstu czatu oraz planowania; wyjaśnienia rekomendacji mają
te same aktywne wersje pamięci i wspólny cel. Nowe informacje nie zastępują
codziennych pomiarów regeneracji i nie przepisują samodzielnie treningów.
Ocena reakcji i adaptacja całego planu pozostają zakresem sprintu 35.

Każdy podgląd profilu ma UUID i wersję źródłowego profilu. Potwierdzenie odbywa
się transakcyjnie, z warunkiem na rewizję stanu i status propozycji. Nieaktualna
propozycja daje 409, zamiast nadpisywać nowsze ustalenie. Ponowienie tej samej
operacji zwraca zapisany wynik; inna treść z tym samym ID lub sprzeczna decyzja
są odrzucane. Odrzucenie nie zmienia profilu ani nie unieważnia innych szkiców.

Zmiana potwierdzonego celu, pamięci lub początku cyklu unieważnia wcześniejszy
podgląd planu przed jego zapisem. Ustalenia są w dotychczasowej trwałej bazie,
a nie w localStorage. Zamknięcie dostępu usuwa dane profilu z dokumentu strony.
Tekst, nazwy startów, cytaty i historia są wyświetlane jako tekst, bez HTML.

## API i zgodność

Nowe endpointy wymagają istniejącego `COACH_CHAT_ACCESS_CODE` w nagłówku Bearer:

- `GET /coach/profile` — aktualne dane, historia wersji i ostatnich 50 propozycji.
- `GET /coach/profile/calendar` — aktualna wersja kalendarza i przyszłe starty A.
- `POST /coach/profile/proposals` — UUID, wersja profilu, zmiana pamięci/cyklu/celu,
  opcjonalnie identyfikator wiadomości i dokładny cytat razem.
- `POST /coach/profile/proposals/{UUID}/decision` — `accept` albo `reject`.

Stary `GET /memory` wymaga teraz prywatnego kodu. Dawne endpointy bezpośredniego
zapisu i nadpisywania pamięci zwracają 410 po autoryzacji; zmiany przechodzą
przez podgląd i potwierdzenie. Feedback treningowy pozostaje dotychczasowy.

Nowe tabele: `athlete_profile_state`, `athlete_memory_details`,
`athlete_profile_proposals`. Tworzy je dotychczasowe `Base.metadata.create_all`.
Istniejące tabele nie wymagają ALTER; dawna pamięć i rozmowy pozostają zachowane.
Nowe szczegóły pamięci są w tabeli powiązanej z istniejącym rekordem.

## Wdrożenie

Wdrożyć backend przed frontendem, zachowując trwałą bazę, dotychczasowe sekrety,
ustawienia Google Sheets i OpenAI. Nie potrzeba nowych sekretów ani kolumn arkusza.
Po wdrożeniu otworzyć profil i potwierdzić aktualny cel A. Datę dnia 1 cyklu
ustawić tylko wtedy, gdy jest ustalona. Rozmowy spoza PaceMind nadal nie są
odczytywane automatycznie; istotne ustalenie można dodać w profilu.

Model korzysta z istniejącego płatnego wywołania czatu i jego limitów;
propozycja pamięci nie uruchamia dodatkowego modelu. Czat nie zapisuje niczego
w Google Sheets. Sprinty 34 (długofalowy plan do A) i 35 (weryfikacja i adaptacja
tego planu) pozostają kolejnymi częściami uzgodnionego szkieletu.

## Weryfikacja

- `cd backend && .venv/bin/python -m pytest tests -q` — **305 passed**.
- `cd tests/frontend && npm test` — **28 passed**.

Nowe testy obejmują potwierdzanie celu, zgodność ze zmienionym kalendarzem,
wybór konkretnego A zamiast pierwszego A, zakończony cel, zachowanie oryginału
pamięci, stan kontuzji po poprawieniu, nieaktualne równoległe podglądy,
idempotencję, cytat zawodnika zamiast odpowiedzi AI, brak automatycznego zapisu
sugestii, wspólne dane planowania, pozycję cyklu, autoryzację i wyłączenie
starego zapisu z pominięciem potwierdzenia. Chromium sprawdza pełny przepływ
celu/cyklu, odświeżenie, propozycję z rozmowy, poprawienie pamięci, historię,
wyświetlanie literalnego HTML, układ telefonu i usunięcie danych po zamknięciu.

Testy używają SQLite oraz kontrolowanego kalendarza i modelu. Produkcyjne
Google Sheets ani model OpenAI nie były wywoływane podczas implementacji.
