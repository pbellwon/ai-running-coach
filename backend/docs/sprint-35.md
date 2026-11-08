# Sprint 35 — weryfikacja i adaptacja zaakceptowanego planu

W Trenerze jest panel **Przegląd wykonania i korekta dalszego planu**.
„Oceń wykonanie i dalszy plan” porównuje ostatni zakończony cykl z zaakceptowaną
wersją planu. Jeżeli cykl jest jeszcze w trakcie, obejmuje tylko zakończone dni,
bez uznawania dzisiejszej otwartej jednostki za opuszczoną. Okno ma do 10 dni;
można też odczytać zachowany przegląd w historii. Raport nie zmienia arkusza.

Przegląd wymaga zaakceptowanego planu oraz zgodności jego celu z potwierdzonym
profilem i kalendarzem. Brak planu daje jasny komunikat o tym warunku, a nie
ocenę, że plan jest dobry. To osobne od zgłoszonego problemu generowania,
który zgodnie z ustaleniem pozostaje do późniejszej weryfikacji produkcyjnej.

## Dane i interpretacja

Wykorzystywane są istniejące obliczenia, bez nowych płatnych wywołań AI:

- `WeeklyReviewService` i `CompositeSessionBuilder`: dopasowanie wykonań,
  logiczne sesje zamiast liczby plików oraz brakujące i dodatkowe jednostki;
- `WorkoutExecutionReviewEngine` i feedback: zgodność bodźca z planem,
  pewność oceny, RPE i komentarze zawodnika;
- `RecoverySnapshotService` i `RecoveryTrendService`: regeneracja w okresie
  przeglądu oraz osobno najnowsze pięć zakończonych dni;
- `GoalProgressService`: istniejące porównanie trendów z okien 28-dniowych,
  wyświetlane z zastrzeżeniem jego ograniczeń.

Wewnętrzne tygodnie służą tylko ponownemu użyciu istniejącego dopasowania.
Raport odfiltrowuje dokładnie wybrany okres cyklu; nie przenosi agregatów
z dni spoza tego okresu. Historia porównywana jest z zaakceptowanym snapshotem,
a nie z przypadkowo zmienionym dzisiaj arkuszem. Uwzględnia również późniejsze
zaakceptowane pojedyncze korekty, jeżeli ich oryginał odpowiada tej jednostce.

Wzrost zgodności z planem ani większa objętość nie są dowodem poprawy formy.
Sygnały zmęczenia nie są diagnozą przetrenowania. Brak synchronizacji nie jest
automatycznie dowodem opuszczenia treningu. Raport pokazuje dowody i ograniczenia.

## Decyzje i ograniczona propozycja

Reguły są jawne i konserwatywne:

- Za mało wiarygodnych ocen, brak wykonania lub mniej niż dwa dni użytecznej
  regeneracji: zbierz dane; nie ma propozycji automatycznej korekty.
- Aktualna lub niepotwierdzona informacja o kontuzji: doprecyzuj ograniczenia;
  brak automatycznej recepty treningowej lub rozpoznania urazu.
- Co najmniej dwie oceny `too_hard` z pewnością od 0,5 oraz sygnał pogorszonej
  regeneracji: można zaproponować zmniejszenie objętości o 20% i spokojny charakter.
- Wysoki lub narastający sygnał zmęczenia przy wystarczających danych: można
  zaproponować zamianę najbliższych mocnych jednostek na spokojny bieg o 70%
  wcześniejszej objętości.
- Pojedyncza trudniejsza sesja lub sam negatywny trend: obserwacja i wyjaśnienie,
  bez automatycznej przebudowy. Zgodne wykonania przy stabilnej regeneracji
  wspierają utrzymanie struktury, bez gwarancji gotowości do startu.

Jeżeli dane wspierają zmianę, zawodnik wybiera zakres: najbliższa możliwa do
korekty jednostka, najbliższe 10 dni albo blok do 30 dni. Powstaje osobny,
niezmienny podgląd przed/po. Dopiero akceptacja zapisuje zmianę. Nie ma
zwiększania intensywności wyłącznie na podstawie dobrego wykonania albo
wyliczonego trendu. Dalsza, zaplanowana progresja poza korygowanym zakresem
pozostaje elementem pierwotnej drogi do A.

Korekta nie zmienia celu, dat zawodów, faz całego przygotowania ani przeszłych
treningów. Zawody, odpoczynek, wielokrotne jednostki jednego dnia, zaakceptowane
pojedyncze korekty oraz ręcznie zmienione komórki treningu są zachowane.
Inne kolumny i wcześniejszy opis pozostają w arkuszu. Na końcu dopisywana jest
obowiązująca jednostka i notka PaceMind z datą, zakresem, powodem i celem A.

## Ten sam plan i kolejne wersje

`active_plan_state` wskazuje aktualną wersję oraz pierwotną kampanię przygotowań.
Przy pierwszym użyciu przejmuje ostatnią zapisaną wersję, nie szkic. Nowy pełny
plan rozpoczyna nową kampanię; zaakceptowana adaptacja wskazuje tę samą kampanię
i poprzednią wersję. Snapshot całego arkusza, cel, oryginalny horyzont i etapy
pozostają zachowane. Kolejny przegląd po korekcie nadal może oceniać minione dni
pierwotnego planu, a nie tylko przyszły zakres ostatniej korekty.

`plan_execution_reviews` przechowuje przeglądy, dowody, wersje źródeł i decyzję.
Korekty używają istniejącej tabeli `race_plan_drafts` z typem
`adaptation-10-day-v1`, `campaign_id`, `parent_plan_id` i `review_id`.
Wersje korekt są widoczne w istniejącej historii planów i korzystają z tej
samej ścieżki akceptacji, także po odświeżeniu przeglądarki.

Przed propozycją oraz przed zapisem kontrolowane są wersja aktywnego planu,
cel, kalendarz, profil, wykonania, odczucia, regeneracja i arkusz. Nowe dane
unieważniają stary podgląd. Zapis ma wspólną trwałą blokadę z pełnymi planami
i pojedynczymi korektami, jeden atomowy batch Sheets i potwierdzenie odczytem.
Ponowienie zapisanego UUID nie duplikuje zmiany. Niepewny wynik pozostaje
zablokowany; odrzucenie niczego nie zapisuje w arkuszu. Równoległe potwierdzanie
wyniku nie może cofnąć wskaźnika aktywnego planu do starszej wersji.

Zmiana kalendarza od zaakceptowania planu wymaga najpierw uzgodnienia nowego
kalendarza i strategii — ograniczona korekta nie dokłada po cichu nowego startu.
Google Sheets nadal nie zapewnia compare-and-swap dla ręcznych edycji między
ostatnim odczytem a zapisem; podczas akceptacji należy wstrzymać ręczną edycję.

## API i wdrożenie

Wszystkie endpointy wymagają dotychczasowego prywatnego kodu Bearer:

- `GET /coach/plan-reviews/current` — bieżąca kampania i wersja.
- `GET /coach/plan-reviews` — ostatnich 30 przeglądów.
- `POST /coach/plan-reviews` — UUID i opcjonalny zakończony dzień `period_end`.
- `POST /coach/plan-reviews/proposals` — UUID, `review_id`, zakres `unit/cycle/block`.
- `POST /coach/plan-reviews/proposals/{UUID}/decision` — accept/reject.

Nowe dwie tabele utworzy istniejące `Base.metadata.create_all`; nie ma ALTER
starych tabel. Zachować dotychczasową trwałą bazę i sekrety. Wdrożyć backend,
a następnie frontend. Układ `plan_import` i `race_calendar` nie zmienia się.
Nie potrzeba nowych sekretów ani dodatkowych wywołań OpenAI.

Sprint zamyka uzgodniony szkielet funkcji MVP. Nie zastępuje późniejszego
sprawdzenia całej aplikacji na danych zawodnika i naprawy zgłoszonych problemów
produkcyjnego generowania planu.

## Weryfikacja

- Backend: `cd backend && .venv/bin/python -m pytest tests -q` — 330 testów.
- Chromium: `cd tests/frontend && npm test` — 32 testy, w tym podgląd i zapis
  adaptacji, brak zaakceptowanego planu oraz uzasadnione pozostawienie planu.
- Test integracji dowodów korzysta z rzeczywistych usług dopasowania sesji,
  zapisanego feedbacku i historii regeneracji w lokalnej bazie. Testy zapisu
  używają kontrolowanego źródła arkusza; nie wykonują zmian w produkcyjnym
  Google Sheets ani wywołań modelu.
