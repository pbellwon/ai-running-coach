# Plan PaceMind — propozycja trenera i cykl 10-dniowy

Generator po korekcie wymagań zastępuje formularz dni tygodnia, limitów czasu,
kilometrażu i tempa przyciskiem **Zaproponuj mój plan**. Zawodnik nie układa
harmonogramu za trenera. Opcjonalnie dopowiada aktualne odczucia lub odpowiada
na konkretne pytanie PaceMind. Zakres dat i zachowanie istniejących treningów
są dostępne w rozwijanych opcjach, z rozsądnymi wartościami domyślnymi.

Przepływ: dane zawodnika i cel → propozycja trenera z uzasadnieniem → podgląd
przed/po w cyklach 10-dniowych → osobna akceptacja → zapis do Google Sheets.
Nie oznacza to gwarancji matematycznie optymalnego planu ani skuteczności
określonego bodźca na podstawie samej korelacji historycznej.

## Dane i interpretacja

`PersonalPlanContext` odczytuje aktualną trwałą bazę:

- treningi z 84 dni: objętość, czas, typy, obciążenie, RPE, tętno i opisy;
- aktywną pamięć zawodnika: ograniczenia, kontuzje i zapisane ustalenia;
- 60 ostatnich zakończonych wymian oraz do 30 starszych wypowiedzi o zdrowiu
  i cyklu; wypowiedzi zawodnika i odpowiedzi AI są rozdzielone;
- 120 ostatnich zapisów feedbacku oraz 28 dni regeneracji;
- istniejące oceny wykonania do 20 ostatnich jednostek, kiedy są dostępne.

Dostęp dotyczy rozmów zapisanych **w PaceMind**. Backend nie ma dostępu do
innych rozmów w ChatGPT. Istotne ustalenia spoza aplikacji można dopowiedzieć
trenerowi albo utrwalić w istniejącej pamięci zawodnika. Długie odpowiedzi AI
są ograniczane do 1000 znaków, z jawną flagą skrócenia; wiadomości zawodnika
pozostają w całości. Skrócone opisy 30 ostatnich aktywności uzupełniają pełne
sumy dni z 84 dni. Aktywna pamięć nie jest skracana.

Kalendarz `race_calendar` jest źródłem dat, dystansów, priorytetów i celów
czasowych startów. Kontuzja historyczna nie oznacza automatycznie aktualnego
bólu; brak zgłoszenia bólu nie potwierdza zdrowia. Przy nierozstrzygniętym
ograniczeniu trener ma zapytać, a nie wygenerować pozornie dopasowany plan.
Informacja z rozmowy nie jest automatycznie dopisywana do pamięci.

## Indywidualna propozycja i granice liczbowe

Istniejący klient OpenAI proponuje strukturę dokładnie 10 dni: spokojne biegi,
kontrolowany próg, długi bieg i odpoczynek, z konkretnymi objętościami, czasem,
odcinkami i uzasadnieniem. Odpowiedź musi wskazać istniejące źródła; walidator
odrzuca wymyślone identyfikatory oraz brak odniesienia do historii.
Stare odpowiedzi AI nie są dowodem zgody zawodnika ani skuteczności treningu.

Plan nie jest podziałem tygodnia na siedem dni. Ma pozycję dnia 1–10 i kolejne
cykle co 10 dni. Jeżeli pozycja w dotychczasowym cyklu jest znana z ustaleń,
trener ją kontynuuje; inaczej jawnie proponuje nowy początek w uzasadnieniu.
Zawody, taper i regeneracja działają na rzeczywistych datach.

Dane dają konserwatywne granice propozycji: kilometraż ostatnich 28 dni
przeliczony na 10 dni, długość i czas obserwowanych jednostek z marginesem
10%. Model nie może sam zwiększyć objętości pierwszego cyklu. Minimum danych
to sześć dni z bieganiem w ostatnich 28 dniach i bieg w ostatnich siedmiu dniach;
przy mniejszej historii nie ma płatnego wywołania modelu ani zgadywania obciążeń.
To kontrola dostępności danych, nie ocena gotowości do startu.

Walidacja wymaga co najmniej dwóch dni odpoczynku, najwyżej jednego długiego
biegu i dwóch akcentów w mikrocyklu. Mocne dni są oddalone co najmniej o trzy
dni, także przy przejściu dzień 10 → dzień 1. Odcinki muszą mieścić się w czasie
jednostki wraz z rozgrzewką, przerwami i schłodzeniem. Niespójna odpowiedź modelu
zwraca błąd bez zapisu i bez zastąpienia jej ogólnym planem tygodniowym.

Kolejne cykle rozwijają tę samą indywidualną strukturę o najwyżej 3% na cykl,
łącznie do 115%; co czwarty cykl jest lżejszy. Taper A/B, starty, regeneracja
zależna od dystansu i zachowane jednostki ograniczają objętość. Akcenty kolidujące
ze startem lub inną mocną jednostką są zastępowane spokojnym biegiem.
Przyszłe cykle są rozwinięciem strategii, nie oddzielnymi prognozami AI.
Po nowych odczuciach lub wykonanych cyklach można zaproponować plan ponownie
z aktualnych danych.

## Zachowane zabezpieczenia i historia

Pozostają: niezmienny podgląd, osobna akceptacja, oryginał i historia opisów,
końcowa notka PaceMind z datą, zakresem i powodem, ochrona zaakceptowanych
pojedynczych korekt, ochrona dni z wieloma jednostkami oraz wspólna trwała
blokada zapisu z modułem korekt sprintu 32. Zmiana danych zawodnika — w tym nowa
rozmowa, informacja o bólu lub feedback — unieważnia wcześniejszy podgląd przed
zapisem, podobnie jak zmiana kalendarza lub arkusza.

Cały plan zapisuje się jednym atomowym `spreadsheets.batchUpdate`, literalnym
tekstem. Zachowane uwagi i inne kolumny nie są przepisywane. Po utracie
odpowiedzi backend sprawdza wynik zamiast ponawiać zapis. Niepewny zapis
pozostaje zablokowany do potwierdzenia lub rozstrzygnięcia przez administratora.
Google Sheets nadal nie oferuje compare-and-swap; ręczna edycja między ostatnim
odczytem a zapisem pozostaje ograniczeniem, więc w czasie akceptacji należy
wstrzymać edycję arkusza.

Stare wersje i tabela dawnych preferencji pozostają dla audytu. Stare podglądy
generatora tygodniowego można oglądać i odrzucić, lecz nie można ich teraz
zaakceptować. Stany już zapisane oraz sprawdzanie rozpoczętego zapisu działają
nadal. Endpoint zapisu dawnych preferencji zwraca 410. Nie ma nowych tabel,
sekretów ani zakładek arkusza.

## Koszt, wdrożenie i sprawdzenie

Model korzysta z istniejących `OPENAI_API_KEY` i `OPENAI_MODEL`, z timeoutem
60 s, bez automatycznych ponowień SDK i z limitem 4500 tokenów odpowiedzi.
Generowanie współdzieli z czatem trwałą bramkę: 10 s odstępu, 60 prób na dobę
UTC i jedno aktywne wywołanie. Bramka jest odnawiana po zebraniu ocen, przed
modelem; wygasła próba nie zapisuje podglądu. Ponowienie zapisanego UUID nie
wywołuje AI ponownie. Awaria modelu nie zmienia arkusza.

Wdrożyć backend przed frontendem, zachowując dotychczasowe sekrety i bazę.
`race_calendar` i `plan_import` mają dotychczasowe kolumny, bez zmian układu.
Testy używają kontrolowanego modelu i arkusza, bez produkcyjnych zapisów.

Weryfikacja końcowa: **290 testów backendu i 23 testy Chromium przeszły**.
Sprawdzono także starszą rozmowę o kontuzji poza ostatnimi 60 wymianami,
ciągłość pozycji w cyklu 10-dniowym, odmowę użycia podglądu ze starego generatora,
walidację źródeł i obciążeń modelu, blokadę akceptacji po nowym zgłoszeniu bólu
oraz ponowienie zapisu bez duplikatów. Rzeczywista odpowiedź modelu produkcyjnego
nie była w tym środowisku wywoływana.
