# Sprint 32A — pełny plan pod kalendarz startów

W zakładce **Trener** dostępny jest panel **Plan pod kalendarz startów**.
Po odblokowaniu prywatnym kodem zawodnik:

1. Wczytuje świeży kalendarz i plan oraz zapisane preferencje.
2. Wybiera 2–6 dni treningowych, dzień długiego biegu, limity minut na każdy
   dzień, obecną tolerowaną objętość tygodniową i spokojne tempo w min/km.
3. Zapisuje preferencje w bazie. Średnia z zarejestrowanych biegów ostatnich
   28 dni jest wskazówką do samodzielnej weryfikacji kompletności historii.
   Nie ustala automatycznie obciążenia i nie zastępuje danych zawodnika.
4. Wybiera okres od jutra (początek najwyżej 30 dni naprzód), do maksymalnie
   366 dni. Okres musi zawierać przynajmniej jeden start główny A.
5. Generuje wersję z porównaniem przed/po wszystkich dni, tygodniami,
   kilometrażem, fazą przygotowań i najbliższym startem A. Sprawdza ostrzeżenia.
6. Osobno akceptuje cały podgląd lub odrzuca wersję. Generowanie nie zapisuje
   niczego w Google Sheets.

Domyślnie koniec okresu przypada siedem dni po najbliższym starcie A; można go
wydłużyć, aby objąć kolejne starty. Kalendarz służy do budowania planu, a nie do
zmiany dotychczasowego źródła celu w innych modułach aplikacji.

## Google Sheets

Dotychczasowy `plan_import` i jego kolumny pozostają kompatybilne. Jedyna nowa
zakładka to `race_calendar` w **tym samym skoroszycie**. Nagłówki w pierwszym
wierszu muszą dokładnie odpowiadać poniższym nazwom:

| date | name | distance_km | priority | target_time | notes |
| --- | --- | --- | --- | --- | --- |
| 2026-12-13 | Bieg główny | 10 | A | 38:30 | Trasa płaska |
| 2026-11-15 | Start kontrolny | 5 | B | | |

`date` ma format YYYY-MM-DD, dystans to dodatnia liczba do 100 km (akceptowany
przecinek dziesiętny), priorytet A/B/C. Wartości `target_time` i `notes` są
opcjonalne, ale ich nagłówki muszą istnieć. Czas: MM:SS lub HH:MM:SS; najlepiej
zapisać go jako zwykły tekst, aby Sheets nie zmienił formatu wyświetlania.
Puste wiersze są pomijane. Dwa starty w jednym dniu, brak nagłówków, niepoprawna
data/liczba lub nieznany priorytet blokują generowanie z komunikatem.

Nie potrzeba zakładek na preferencje, szkice ani historię — są w trwałej bazie.
Opcjonalna zmienna `GOOGLE_RACE_WORKSHEET_NAME` zmienia nazwę `race_calendar`.
Pozostałe ustawienia arkusza i konto Google są wspólne ze sprintem 32.

## Reguły generowania

Generator jest deterministyczny i nie wywołuje płatnego modelu. Bazuje na jawnie
zapisanych warunkach zawodnika oraz datach, dystansach i priorytetach startów.
Nie estymuje formy i nie wyprowadza tempa treningowego z docelowego czasu.
Tekst uwag jest zachowywany jako tekst, nie jako instrukcja generatora.

- Przygotowania obejmują bazę, budowanie, specyfikę startową, tygodnie lżejsze,
  taper i regenerację. Kolejny start A rozpoczyna kolejny cykl po regeneracji.
- Wzrost budżetu tygodniowego: 5% na tydzień cyklu, maksymalnie do 130% wskazanej
  objętości. Co czwarty tydzień obniża budżet o 20%.
- W ostatnich dwóch tygodniach A budżet wynosi najwyżej 70%, a w tygodniu startu
  50% bazowej objętości. Tydzień B ma limit 80%; C nie powoduje osobnego taperu.
- Start zastępuje jednostkę dnia i zużywa budżet kilometrowy tygodnia.
  Start poza wybranym dniem treningowym jest widocznym wyjątkiem w ostrzeżeniu.
- Długi spokojny bieg ma większy udział w objętości (większy dla startów ponad
  10 km), lecz respektuje limit minut zawodnika. Akcent kontrolowanego progu
  pojawia się najwyżej raz na tydzień po bazie; długość odcinków zależy od etapu,
  dystansu najbliższego A i czasu jednostki. Nie ma akcentów w tygodniach taperu
  ani w siedmiu dniach poprzedzających start. Dni z innymi mocnymi sesjami i starty
  uwzględniane są przy zapewnianiu odstępu co najmniej trzech dni.
- Po starcie do 10 km są dwa dni bez nowego biegania, po starcie do 21,1 km
  cztery, do 42,2 km siedem, powyżej dziesięć. Zbyt bliskie kolejne zawody
  generują jawne ostrzeżenie, bez usuwania startów zawodnika.
- Każdy pozostały dzień ma konkretną jednostkę lub odpoczynek. Czasy zwykłych
  jednostek nie przekraczają limitu dnia. Jednostka krótsza niż 15 min jest
  zastępowana odpoczynkiem. Czas zawodów nie jest prognozowany.
- Starty i zachowane treningi odejmowane są od dostępnego kilometrażu;
  generator nie dokłada pełnego tygodnia obok istniejącego planu. Niepełne tygodnie
  mają proporcjonalny budżet. Limity mogą uniemożliwić wykorzystanie całej objętości
  — podgląd pokazuje rzeczywisty kilometraż i ostrzega o dużej różnicy.

Bieżące sygnały regeneracji nadal obsługuje istniejący moduł korekt ze sprintu 32;
nowy generator nie zastępuje codziennej oceny ani nie zapisuje odczuć do pamięci.

## Ochrona istniejącego planu

Domyślnie generator **uzupełnia puste dni** i zachowuje wszystkie istniejące
wiersze. Opcja przebudowy pozwala zastąpić pojedyncze, niechronione jednostki
w wybranym przyszłym okresie. Nie zmienia dat istniejących wierszy i nie usuwa
wierszy. Dni z wieloma jednostkami oraz zaakceptowane pojedyncze korekty są
chronione; nie są scalane ani zastępowane generatorem.

W przebudowanym opisie zachowane są wcześniejsza treść, uwagi i historia,
po nich obowiązujący trening oraz końcowa notka PaceMind z datą, zakresem
zmiany i uzasadnieniem. Pozostałe kolumny i priorytet istniejącego wiersza
pozostają nietknięte. Oryginalny i wynikowy arkusz zapisane są także w audycie
wersji w bazie. Kolejna przebudowa wygenerowanego planu jest możliwa; późniejsza
pojedyncza korekta ponownie chroni daną jednostkę.

Zachowane jednostki mogą ograniczyć taper lub regenerację — podgląd ostrzega
o tym jawnie. Jeśli zachowany trening w dniu startu nie odpowiada zawodom,
podgląd ma konflikt i akceptacja jest zablokowana. Trzeba skorygować jednostkę
osobno albo wybrać przebudowę, jeśli wiersz nie jest chroniony.

## Trwałość i bezpieczne ponowienia

Nowe tabele: `training_preferences` i `race_plan_drafts`. Tworzy je dotychczasowe
`Base.metadata.create_all`, bez zmian istniejących tabel. Preferencje zapisują się
z kontrolą wersji. Historia pokazuje ostatnich 30 wersji planu, starsze pozostają
w bazie. Każdy podgląd jest niezmiennym rekordem z UUID, źródłami, preferencjami,
stanem, pełnym audytem oryginału i wyniku oraz porównaniem jednostek.

Przed zapisem backend ponownie odczytuje **cały plan i kalendarz**, porównuje ich
wersje oraz aktualne preferencje i sprawdza, czy początek nie jest już miniony.
Zmiana uwag, kolejności wierszy, daty startu lub celu czasowego także unieważnia
podgląd. Akceptacja przesyła wyłącznie ID i decyzję, nigdy zmodyfikowane wiersze.

Całość zapisuje się jednym atomowym żądaniem Sheets `spreadsheets.batchUpdate`
z `updateCells` i ewentualnym zwiększeniem liczby wierszy. Nie ma sekwencyjnego
zapisu kolejnych treningów. Istniejące niezmienione komórki, w tym dodatkowe
kolumny, nie są przepisywane. Tekst zapisuje się jako `stringValue`, więc nazwa
lub uwaga zaczynająca się od `=` nie staje się formułą. Nowe dni są dopisywane na
końcu arkusza, aby zachować identyfikację fizycznych wierszy istniejących korekt.

Pełny plan i pojedyncze korekty używają tej samej trwałej blokady
`plan_write_gate`. Dwa zapisy PaceMind nie nakładają się. Ponowienie tego samego
UUID zwraca istniejący podgląd/wynik; inna treść z tym samym ID daje 409.
Po błędzie lub utracie odpowiedzi backend sprawdza pełną zgodność arkusza
z oczekiwanym wynikiem. Nie wysyła planu ponownie. Niepewny stan `writing`
pozostaje zablokowany także po restarcie. Przycisk i historia pozwalają ponowić
**sprawdzenie wyniku**, bez drugiego dopisania dni.

Jeśli zgodności nie da się potwierdzić, administrator porównuje `before_snapshot`
i `after_snapshot` z rzeczywistym arkuszem w `race_plan_drafts.payload`.
Procedura rozstrzygnięcia blokady odpowiada sprintowi 32: po upewnieniu się,
że żaden poprzedni proces nie może już wysłać zapisu, transakcyjnie oznaczyć
wersję jako `stale` i wyczyścić właściciela bramki tylko dla jej UUID. Nie należy
zwalniać niepewnego zapisu automatycznie.

Google Sheets nadal nie oferuje atomowego warunku „zapisz, jeśli komórki mają
poprzednie wartości”. Ręczna edycja między ostatnim odczytem a żądaniem zapisu
pozostaje możliwa; podczas akceptacji planu należy wstrzymać ręczne edycje.
Atomowy batch chroni przed częściowym zapisem, a blokada przed jednoczesnymi
zapisami PaceMind; wymaga wspólnej trwałej bazy dla wszystkich instancji.

## API i wdrożenie

Wszystkie endpointy wymagają dotychczasowego prywatnego kodu Bearer i zwracają
`Cache-Control: no-store`:

- `GET /coach/race-plans/context` — świeży kalendarz, wersje planu i ustawień.
- `PUT /coach/race-plans/preferences` — `version` i `value` z preferencjami.
- `POST /coach/race-plans/preview` — UUID `id`, `plan_version`,
  `calendar_version`, `preferences_version`, `start`, `end`, `replace_existing`.
- `GET /coach/race-plans` — ostatnie wersje.
- `GET /coach/race-plans/{UUID}` — pełny podgląd zapisanej wersji.
- `POST /coach/race-plans/{UUID}/decision` — `decision: accept` albo `reject`.

Nie potrzeba nowych sekretów. Konto Google musi mieć prawo edycji skoroszytu.
Wdrożyć backend przed frontendem, zachowując dotychczasową trwałą bazę:

```sh
gcloud run deploy pacemind-backend --source backend --region=europe-central2 --project=pacemind-503211
npx --yes firebase-tools deploy --only hosting --project=pacemind-503211
```

## Weryfikacja

- Backend: `cd backend && .venv/bin/python -m pytest tests -q` — **288 passed**.
- Chromium: `cd tests/frontend && npm test` — **22 passed**.

Testy obejmują walidację kalendarza i ustawień, cały okres z odpoczynkiem,
wiele startów A, starty B/C, taper, regenerację, limity czasu i kilometrażu,
odstępy między mocnymi jednostkami, ochronę korekt i wielu jednostek dnia,
zachowanie oryginału i innych kolumn, ponowną przebudowę, przestarzałe źródła,
autoryzację, odrzucenie i konflikt decyzji, utratę odpowiedzi, wspólną bramkę
z pojedynczymi korektami oraz atomowy batch z literalnym tekstem.
Przeglądarka sprawdza podgląd, zapis, ponowne otwarcie historii i preferencji,
zmianę kalendarza, ponowienie po utracie odpowiedzi, tekst HTML i szerokość telefonu.
Google Sheets jest zastąpiony kontrolowanym źródłem; produkcyjny arkusz nie był
odczytywany ani zmieniany w trakcie implementacji. Jego nagłówki i uprawnienia
zostaną zweryfikowane przy wczytaniu panelu po wdrożeniu.
