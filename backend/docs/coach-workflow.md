# Trener — rozmowa i pełny plan przygotowań

Po otwarciu prywatnego dostępu są dwie sekcje: rozmowa i planowanie.
Profil jest rozwijany pod rozmową; przeglądy wykonania, pojedyncze korekty
i historie są rozwijane w planowaniu. Dotychczasowe dane i endpointy pozostają.

Planowanie pokazuje cel A z `race_calendar` i początek przygotowań.
Wybór innego celu wymaga przycisku „Potwierdzam ten cel główny”. Samo wybranie
opcji nie zmienia profilu. Przygotowanie planu tworzy niezmienny podgląd faz,
cykli 10-dniowych i konkretnych jednostek. Dopiero osobna akceptacja zapisuje
treningi do Google Sheets. Koniec wynika z wybranego A i okresu regeneracji;
nie ma formularza godzin, dni tygodnia ani osobnego ręcznego końca planu.

Nowy start B/C można dodać później w arkuszu i odświeżyć kalendarz.
Start B ma rolę kontrolną, a C jest bodźcem w przygotowaniach bez osobnego szczytu formy.
Jeśli cel i początek pozostają te same, propozycja wskazuje aktualny
`parent_plan_id` i zachowuje `campaign_id`, pierwotny początek i fazy.
Aktualizacja obejmuje najwcześniej jutro. Zachowuje pozycję cyklu, przeszłe
jednostki, komentarze, indywidualne korekty i wykryte ręczne zmiany; ich
ochrona przechodzi do dalszych wersji. Zmiana aktywnej wersji po podglądzie
blokuje zapis, także gdy same komórki arkusza są identyczne.

`GET /coach/race-plans/context` zawiera krótkie `active_plan` z flagą
`calendar_changed`; `POST /coach/race-plans/preview` przyjmuje opcjonalny
`parent_plan_id`. Początek nowych przygotowań może być do roku naprzód,
a horyzont ma nadal najwyżej 366 dni. Pozostałe kontrole wersji, wspólna
blokada zapisu, idempotencja i odczyt potwierdzający pozostają wspólne.

Czat ma świeże miesięczne podsumowania całej historii zapisanej w bazie,
liczone na logicznych sesjach. Widzi także ostatnie oznaczone zawody oraz
najlepsze zapisane wyniki na poszczególnych dystansach; dawne rekordy
pozostają datowane. Czas zawodów pochodzi z oznaczonej aktywności, bez
doliczania osobnej rozgrzewki lub schłodzenia. Nie jest zweryfikowanym czasem
oficjalnym. Szczegółowe oceny, odczucia i regeneracja korzystają z istniejącego
świeżego kontekstu; podsumowanie archiwum nie udaje szczegółowej oceny każdego
starego treningu. Nieprawidłowe czasy i dystanse są pomijane i raportowane.

Pytanie „Czy mój czas jest realny?” przygotowuje pytanie do czatu.
Instrukcja pozwala na jakościową opinię z dowodami i brakami, bez wymyślania
szans procentowych, prognoz czasu lub nowych wskaźników gotowości.
Brak historii nie może stawać się potwierdzeniem celu. Odpowiedź modelu
pozostaje interpretacją, wymagającą weryfikacji na rzeczywistych danych.

Nie ma zmian w układzie Sheets, nowych tabel ani nowych sekretów. Wdrożyć
backend przed frontendem. Testy korzystają z lokalnej bazy, kontrolowanego
arkusza i odpowiedzi modelu; nie zapisują niczego w produkcyjnym arkuszu
i nie oceniają jakości odpowiedzi rzeczywistego modelu.

Weryfikacja: 342 testy backendu i 35 testów Chromium, w tym wybór innego
celu przez formularz, pełny podgląd oraz nowy start B w tej samej kampanii.
