# Generowanie planu — format, poprawka odpowiedzi i diagnostyka

Komunikat „Nie udało się przygotować spójnej propozycji trenera” w poprzedniej
wersji oznaczał wspólnie błąd dostawcy, uciętą odpowiedź, niepoprawny JSON lub
naruszenie reguł planowania. Nie powstawał wtedy draft ani podgląd. Sam zrzut
tego komunikatu nie pozwala ustalić konkretnej przyczyny produkcyjnego żądania.

Planowanie wysyła teraz schemat JSON do Responses API w trybie strict.
Wszystkie pola obiektów są wymagane, a cytowane źródła są ograniczone do
identyfikatorów dostępnych w kontekście. Pozostałe użycia klienta nadal mogą
generować tekst. Limity długości pojedynczej sesji są przekazywane także
w samym schemacie, zgodnie z obserwowaną historią. Status incomplete, brak tekstu i odmowa nie są traktowane
jako poprawny plan, nawet jeżeli częściowy tekst wygląda jak JSON.

Po niepoprawnym formacie lub naruszeniu reguły silnik może jeden raz poprosić
model o poprawienie całej propozycji, przekazując jej błąd i te same limity.
Nie skaluje po cichu obciążeń ani nie podstawia ogólnego szablonu. Poprawiona
propozycja przechodzi te same kontrole historii, źródeł, odstępów, objętości,
zdrowia i kompletności 10 dni. Nierozstrzygniętego stanu zdrowia w gotowej
propozycji nie naprawia przez ponawianie aż do uzyskania deklaracji zdrowia.

Drugie wywołanie zużywa osobną próbę ze wspólnego limitu dziennego. Przed
każdym wywołaniem i po odpowiedzi sprawdzane jest posiadanie aktualnej dzierżawy.
Nie ma automatycznej poprawki po błędzie dostępu, konfiguracji, limicie,
timeout lub przerwaniu odpowiedzi. Każde wywołanie ma timeout 35 sekund
i wyłączone dodatkowe ponowienia SDK.

Niepowodzenie generowania ma osobną kartę „Plan nie został wygenerowany”
z powodem, kodem zgłoszenia i przyciskiem ponowienia. `detail` takiego błędu
w API zawiera message, code, reference, issues i plan_generated=false.
Zwykłe błędy zachowują dotychczasowy tekstowy detail. Żaden błąd nie odsłania
starego przycisku akceptacji ani nie zapisuje jednostek do Sheets.

Log `pacemind_plan_failure` zawiera kod zgłoszenia, kategorię i nazwę reguły,
typ/status błędu dostawcy oraz wyłącznie rozpoznany kod dostawcy. Nie zawiera
promptu, odpowiedzi modelu, danych zawodnika, klucza ani treści wyjątku.
Pozwala to po wdrożeniu skorelować zgłoszenie z logami Cloud Run.

Poprawka nie zmienia konfiguracji modelu, sekretów ani układu arkusza.
Wdrożyć backend oraz frontend. Testy używają kontrolowanych odpowiedzi
wadliwych i poprawnych; nie potwierdzają przyczyny wcześniejszego żądania
produkcyjnego ani skuteczności odpowiedzi rzeczywistego dostawcy na nim.

Weryfikacja: 352 testy backendu i 37 testów Chromium. Obejmuje rzeczywiste
SDK OpenAI z lokalnym transportem HTTP, poprawienie odrzuconego cyklu,
blokadę po utracie dzierżawy lub wyczerpaniu limitu oraz przejście od
widocznego błędu do podglądu i pojedynczego zaakceptowanego zapisu.
