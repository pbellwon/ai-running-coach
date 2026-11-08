# Siła i praca progowa w przygotowaniach

Poprzednia wersja nie dopuszczała rodzaju `strength`, a w rozwijaniu planu
dla dystansu ponad 10 km nadpisywała propozycję trenera dawką 2×4 lub 2×8 min.
To ograniczenie generatora nie wynikało z indywidualnej oceny zawodnika.

Siła jest teraz osobną jednostką: zero kilometrów, czas oraz konkretne ćwiczenia
z seriami i powtórzeniami. Nowy kontekst wymaga 1–2 takich jednostek na 10 dni,
co najmniej jednego pełnego odpoczynku i dwóch dni bez biegania. Przy braku
historii siły limit wprowadzenia wynosi 20 min; obserwowane sesje mogą podnieść
go do 45 min. Nie jest to ocena tolerancji ciężaru maksymalnego. Siła pozostaje
co najmniej dwa dni od progu/długiego biegu, również na granicy cykli. Starty,
chronione jednostki, taper i regeneracja mogą powodować jej jawne pominięcie.
Całkowity brak siły w dłuższej propozycji, która miała ją zawierać, blokuje zapis.

`PlanTrainingEvidence` odczytuje wykonane sesje i rozpoznane odcinki z `LapDB`.
Rozgrzewka, schłodzenie i sam czas całej sesji nie stają się minutami progu.
Wynik zawodów ani trening oznaczony tylko jako tempo nie służą jako dowód
dawki progowej. Sesje z wysokim zgłoszonym wysiłkiem lub odczuciem too_hard
pozostają w dowodach, ale nie podnoszą referencji obciążenia. Brak odcinków
nie jest interpretowany jako brak doświadczenia. Dane odcinków i ich interpretacja
wchodzą do wersji kontekstu; ich zmiana unieważnia stary podgląd.

Propozycja może zawierać 1–6 odcinków po 2–40 min, również jeden odcinek ciągły.
W pierwszym cyklu nie przekracza rozpoznanej dawki, jeśli ta jest dostępna.
Silnik zachowuje liczbę odcinków i przerwy dobrane przez trenera. Faza wpływa
na dawkę: baza do 80%, rozwój do 100%, specyfika do 120% odniesienia. Praca
narasta od aktualnego ziarna do górnego pułapu w czasie dostępnych przygotowań,
z zachowaniem odciążeń, taperu, odstępów i faktycznego czasu całej jednostki.
Bez rozpoznanej historii pozostaje ograniczona dawką z propozycji i dotychczasową
obwiednią progresji. Mniejsza dawka po przerwie nie jest wiecznym limitem 2×8,
ale późniejsze zwiększenie jest propozycją wymagającą przeglądów, nie dowodem
przyszłej tolerancji. Aktualizacja w późnej fazie zaczyna rampę od bieżącej dawki,
zamiast traktować minione miesiące jako wykonaną progresję.

W podglądzie cyklu widać minuty pracy progowej i liczbę sesji siłowych. Dla
zachowanych progów, których dawki nie przeliczono, widoczny jest brak wartości.
Dotyczy to także cyklu przeciętego aktualizacją oraz cyklu objętego późniejszą
korektą obciążeń; dawne minuty nie są przedstawiane jako nowa dawka.
Cel 1:27 nie narzuca automatycznej dawki ani tempa. Test z historią 3×10 min
sprawdza dłuższy bodziec i przypadek powrotu od 2×4 min; nie wyznacza treningów
dla każdego zawodnika ani nie potwierdza gotowości konkretnego użytkownika.

Układ Sheets i ścieżka podgląd → akceptacja → zapis pozostają bez zmian.
Wdrożyć backend i frontend, a następnie wygenerować nową propozycję.
Stare wersje i zaakceptowane korekty pozostają w historii; poprawka nie zmienia
produkcyjnego planu bez decyzji zawodnika.

Weryfikacja: 365 testów backendu i 37 testów Chromium. Obejmuje rozpoznanie
rzeczywistych odcinków 3×10 min w lokalnej bazie, odróżnienie od 52 min całej
sesji, wpływ feedbacku, wersjonowanie odcinków, samodzielną siłę, kontrolę
odstępów i czasu jednostek oraz ostrożny pierwszy cykl późnej aktualizacji.
To testy logiki i kontrolowanych danych, nie ocena gotowości konkretnego
zawodnika ani weryfikacja odpowiedzi produkcyjnego modelu.
