# Sprint 34 — długofalowy plan do potwierdzonego startu A

Panel Trener pokazuje jedną drogę od wybranej daty do głównego startu i regeneracji:
listę etapów z datami, rolę kolejnych cykli 10-dniowych, objętości oraz konkretne
jednostki. Każdy dzień ma trening, zawody albo odpoczynek. Plan nie powstaje od
nowa przy końcu mikrocyklu. Szkic całej wersji wymaga osobnej akceptacji.

## Strategia całego okresu

`LongTermPlan` rozdziela dostępny czas przed taperem na bazę, rozwój obciążenia
i etap specyficzny dla dystansu. Taper trwa 10 dni dla startu do 10 km, 14 dni
do półmaratonu i 21 dni dla dłuższych startów. Gdy czasu jest mało, etapy są
krótsze lub znikają, a podgląd ostrzega, że plan nie zastępuje przygotowań.
Po starcie uwzględniana jest regeneracja. Domyślny koniec to co najmniej siedem
dni po A, a dla dystansów ponadmaratońskich co najmniej dziesięć.

Model nadal wybiera indywidualną strukturę bodźców na podstawie historii,
odczuć, pamięci i potwierdzonego profilu. W instrukcji otrzymuje cały horyzont
oraz rolę fundamentu w długofalowym planie. Matematyczny silnik rozwija osobno
etapy przygotowań; nie zleca modelowi niezależnego planu dla każdego cyklu.
Nie ma dodatkowych wywołań modelu, nowego formularza dostępności ani nowych
sekretów. Tempo docelowe pozostaje celem zawodnika, nie prognozą formy.

Cykl pozostaje zakotwiczony w potwierdzonej dacie dnia 1. Pierwszy i ostatni
cykl mogą być niepełne. Etapy mają dokładne daty; cykl przecinający granicę
pokazuje oba etapy. Baza ogranicza akcenty, rozwój wprowadza kontrolowaną pracę,
a specyfika zmienia długość i liczbę odcinków zależnie od dystansu A. Taper oraz
regeneracja ograniczają obciążenie. Zachowane są przerwy między mocnymi dniami,
rozgrzewka, przerwy odcinków i schłodzenie. Gdy dawka nie mieści się w czasie,
jednostka zostaje spokojnym biegiem.

Progresja następnego szczytu objętości ma limit 4% względem poprzedniego szczytu,
łącznie najwyżej 140% indywidualnego punktu wyjścia. Co trzeci cykl przygotowań
jest lżejszy o 20%; powrót po odciążeniu porównuje się z poprzednim szczytem,
a nie z obniżoną objętością. Pierwszy cykl nie zwiększa obserwowanego obciążenia.
Długość pojedynczej jednostki i łączna praca progowa również mają stopniowo
rosnącą granicę od punktu wyjścia. Nie narzuca się uniwersalnej dawki akcentu
osobie, która wcześniej tolerowała mniejszą. To propozycja przyszłej progresji,
a nie potwierdzenie gotowości lub gwarancja osiągnięcia czasu.

## Starty B/C i jeden cel

Wybrany w sprincie 33 cel A steruje etapami i taperem, nawet jeśli w arkuszu
jest wcześniejszy start A. Dodatkowe A są jawnie opisane w ostrzeżeniu; nie
zmieniają potwierdzonego celu. B dostaje krótkie ograniczenie obciążenia przed
startem, C nie wywołuje osobnego taperu. Każdy start liczy się jako obciążenie,
zastępuje jednostkę dnia i pociąga regenerację zależną od dystansu.
Zbyt bliskie starty oraz zbyt mała tolerowana długość wybiegań względem celu
mają ostrzeżenia do przejrzenia przed akceptacją.

## Jedna wersja, zachowana historia

Strategia, granice etapów, rola i punkt przeglądu każdego cyklu oraz wszystkie
jednostki zapisują się razem w istniejącym `race_plan_drafts`. Nowe pole
`long_term` opisuje całą drogę. Nie ma nowej bazy ani tabeli. Zmiana danych,
kalendarza lub profilu przed akceptacją unieważnia podgląd. Akceptacja zapisuje
całość jednym dotychczasowym atomowym żądaniem Sheets, ze wspólną blokadą
zapisów, sprawdzeniem wyniku i bez automatycznego odtwarzania niepewnej operacji.

Oryginały, dodatkowe kolumny i historia pozostają zachowane. Pojedyncze
zaakceptowane korekty i dni z wieloma jednostkami są chronione. Podgląd ostrzega,
jeśli zachowane treningi ograniczają zamierzoną strukturę. Nie są nadpisywane
wyłącznie dla osiągnięcia liczby planowanych kilometrów.

Wersja generatora to `long-term-10-day-v1`. Dawne oczekujące podglądy należy
wygenerować ponownie. Wcześniejsze zapisane wersje można nadal odczytać,
a rozpoczęty zapis nadal można potwierdzić. Zabezpieczenia i ograniczenie
ręcznych edycji arkusza między odczytem a zapisem pozostają jak w sprincie 32.

## Wdrożenie i granice sprintu

Nie ma zmian kolumn `race_calendar` lub `plan_import`, nowych sekretów ani
migracji tabel. Wdrożyć backend przed frontendem, zachowując trwałą bazę.
Po wdrożeniu: potwierdzony cel A → Zaproponuj mój plan → sprawdzenie etapów,
cykli i jednostek → akceptacja całego planu. Zakres dat pozostaje w opcjach;
można wybrać początek grudnia i koniec po marcowym A.

Punkt przeglądu na końcu cyklu wskazuje na wykonanie, odczucia i regenerację.
Automatyczna ocena tych danych i propozycje zmian dalszej części tej samej
wersji należą do sprintu 35. Sprint 34 nie uruchamia ponownego planowania
samoczynnie ani nie oznacza przyszłej poprawy formy jako pewnego faktu.

## Weryfikacja

Backend: **311 passed** (`cd backend && .venv/bin/python -m pytest tests -q`).
Chromium: **28 passed** (`cd tests/frontend && npm test`). Dodatkowo po dopracowaniu
uzasadnień na granicy etapów przeszło 36 testów generatora i zapisu.
Sprawdzono grudzień–marzec, kompletność dni, różne dawki w etapach, granicę
wzrostu względem poprzedniego szczytu, odciążenia, wybrany A przy innych startach,
taper, regenerację, krótki horyzont, ograniczenie akcentów do indywidualnej dawki,
widoczność drogi do A oraz istniejące testy akceptacji i ponowień bez duplikatów.
Źródła Sheets i model w testach są kontrolowane; nie wywoływano produkcyjnego
modelu ani nie zapisywano produkcyjnego arkusza.
