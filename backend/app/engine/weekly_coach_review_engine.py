"""Evidence-based weekly coaching; calculations stay independent of an LLM."""
from collections import Counter


class WeeklyCoachReviewEngine:
    def review(self, weekly: dict, recovery: dict, goal=None) -> dict:
        summary = weekly["summary"]
        sessions = [session for day in weekly["days"] for session in day["executed_sessions"]]
        reviews = [session["execution_review"] for session in sessions]
        counts = Counter(review["status"] for review in reviews)
        reliable = Counter(
            review["status"] for review in reviews if review["confidence"] >= 0.5
        )
        assessed = sum(counts[status] for status in ("on_target", "too_hard", "too_easy"))
        positives, attention, next_steps = [], [], []

        def add(target, code, text, *evidence):
            target.append({"code": code, "text": text, "evidence": list(evidence)})

        if reliable["on_target"]:
            add(positives, "on_target", "Część wykonanych sesji odpowiadała założeniom planu.",
                f"{reliable['on_target']} sesji z oceną on_target i pewnością co najmniej 0,5.")
        if summary["paired_workouts_count"]:
            add(positives, "plan_execution", "W historii są wykonania dopasowane do planu.",
                f"Dopasowano {summary['paired_workouts_count']} z {summary['planned_training_count']} zaplanowanych jednostek.")
        completed_rest_days = sum(day["status"] == "off_completed" for day in weekly["days"])
        if completed_rest_days:
            add(positives, "rest_days", "Nie znaleziono treningów w zaplanowane dni odpoczynku.",
                f"Zakończone dni odpoczynku bez zapisanych sesji: {completed_rest_days}.")

        hard = reliable["too_hard"]
        fatigue = recovery["fatigue_signal"]
        if hard:
            add(attention, "too_hard", "Wykonanie części sesji wskazuje na większe obciążenie niż zakładano.",
                f"Sesje too_hard z pewnością co najmniej 0,5: {hard}.")
        if hard >= 2:
            add(next_steps, "repeated_difficulty", "Przed kolejną mocną jednostką oceń regenerację; rozważ mniejszą objętość zamiast dokładania obciążenia.",
                f"Powtarzający się sygnał too_hard: {hard} sesji w tygodniu.")
        elif hard == 1:
            add(next_steps, "observe_difficulty", "Zapisz odczucia po trudnej sesji i obserwuj gotowość do następnego akcentu.",
                "Pojedyncza trudniejsza sesja nie potwierdza narastającego zmęczenia.")
        if fatigue in {"accumulating", "high", "watch"}:
            add(attention, "recovery", "Ostatnie dostępne dni tygodnia zawierają sygnały pogorszonej regeneracji.",
                f"Sygnał zmęczenia: {fatigue}; ocenione dni regeneracji: {recovery['available_days']}.",
                *recovery["trend"]["reasons"])
            add(next_steps, "protect_recovery", "Nadaj priorytet regeneracji i ponownie oceń gotowość przed zwiększeniem intensywności.",
                f"Regeneracja na koniec analizowanego okresu: {fatigue}.")
        if reliable["too_easy"]:
            add(attention, "too_easy", "Niektóre jednostki miały mniejszy bodziec niż zakładano; nie oznacza to automatycznie potrzeby podnoszenia intensywności.",
                f"Sesje too_easy z pewnością co najmniej 0,5: {reliable['too_easy']}.")
            add(next_steps, "check_easy", "Sprawdź powód skrócenia sesji i swój feedback przed zmianą kolejnych treningów.",
                "Ocena too_easy może wynikać z mniejszej objętości, a nie z poprawy formy.")
        if summary["missed_workouts_count"]:
            add(attention, "missing_execution", "Dla części zakończonych dni brakuje wykonania odpowiadającego planowi.",
                f"Niedopasowane jednostki z przeszłych dni: {summary['missed_workouts_count']}.")
            add(next_steps, "verify_import", "Sprawdź synchronizację i brakujące zapisy. Nie nadrabiaj automatycznie kilku jednostek naraz.",
                "Brak zapisu nie rozstrzyga, czy trening rzeczywiście został opuszczony.")
        if summary["type_mismatch_workouts_count"]:
            add(attention, "type_mismatch", "Część wykonanych treningów miała inny charakter niż przewidywał plan.",
                f"Niedopasowania typu: {summary['type_mismatch_workouts_count']}.")
            add(next_steps, "review_substitutions", "Sprawdź, czy zamiany charakteru sesji były celowe i czy kolejny tydzień nadal realizuje założenia planu.",
                f"Wykonania innego typu niż plan: {summary['type_mismatch_workouts_count']}.")
        if summary["unplanned_workouts_count"] or summary["trained_on_off_day_count"]:
            add(attention, "extra_training", "Dodatkowe sesje również wnoszą obciążenie do tygodnia.",
                f"Sesje poza planem: {summary['unplanned_workouts_count']}; dni odpoczynku z treningiem: {summary['trained_on_off_day_count']}.")
            add(next_steps, "count_extra_load", "Uwzględnij dodatkowe treningi przy ocenie kolejnego tygodnia i zachowaj miejsce na odpoczynek.",
                "Ocena obejmuje logiczne sesje, nie liczbę plików aktywności.")

        limitations = []
        if not sessions:
            limitations.append("Brak zapisanych sesji wykonanych w tym tygodniu; nie można ocenić ich trudności.")
        if not summary["planned_training_count"]:
            limitations.append("Brak jednostek treningowych w planie; ocena zgodności z planem jest ograniczona.")
        uncertain = sum(
            review["confidence"] < 0.5 or review["status"] == "insufficient_evidence"
            for review in reviews
        )
        if uncertain:
            limitations.append(f"Sesje z niewystarczającymi dowodami lub niską pewnością: {uncertain}.")
        if recovery["available_days"] < 3:
            limitations.append("Mało dni z danymi regeneracji; brak sygnału zmęczenia nie potwierdza pełnej regeneracji.")
        elif fatigue == "insufficient_data":
            limitations.append("Dane regeneracji z końca tygodnia nie wystarczają do oceny aktualnego trendu.")
        if recovery["missing_baseline_days"]:
            limitations.append("Część pomiarów regeneracji nie ma wystarczającej bazy odniesienia.")
        if sessions and not any(review.get("athlete_feedback") for review in reviews):
            limitations.append("Brak subiektywnego feedbacku do wykonanych sesji.")
        limitations.append("Oceny wykonania opisują zgodność bodźca z planem; nie są pomiarem formy.")
        limitations.append("Porównanie opiera się na aktualnym planie; późniejsze edycje mogą zmienić ocenę historycznych sesji.")

        if not next_steps:
            if reliable["on_target"]:
                add(next_steps, "continue_observing", "Zachowaj strukturę planu i obserwuj regenerację przed kolejnymi akcentami.",
                    "W ocenionych sesjach nie znaleziono powtarzającego się sygnału too_hard.")
            else:
                add(next_steps, "collect_data", "Uzupełnij zapisy treningów, plan i feedback, zanim wyciągniesz mocniejsze wnioski.",
                    "Dostępne dane nie wystarczają do oceny odpowiedzi na cały tydzień.")

        if hard >= 2 or fatigue in {"accumulating", "high"}:
            verdict, headline = "caution", "Warto dać regeneracji pierwszeństwo"
        elif not assessed or not any(reliable[key] for key in ("on_target", "too_hard", "too_easy")):
            verdict, headline = "insufficient_data", "Potrzebujemy więcej danych do oceny tygodnia"
        elif attention:
            verdict, headline = "review", "Tydzień zawiera punkty wymagające uwagi"
        else:
            verdict, headline = "on_track", "Ocenione sesje były zgodne z założeniami"

        return {
            "verdict": verdict,
            "headline": headline,
            "summary": (
                "Ten tydzień dostarczył bodźców treningowych, ale sygnały przeciążenia wymagają ostrożności: daj organizmowi czas na ich przyswojenie."
                if verdict == "caution" else
                "Nie wszystkie elementy tygodnia da się jeszcze ocenić. Sprawdź poniżej, co wspierało przygotowania i co wymaga uwagi."
                if verdict == "review" else
                "Wykonane zgodnie z planem sesje wspierały ciągłość przygotowań. To dowód realizacji bodźca, a nie jeszcze potwierdzenie poprawy formy."
                if verdict == "on_track" else
                "Brakuje wiarygodnych ocen wykonania, aby powiedzieć, jak organizm odpowiedział na ten tydzień. Sam zapis aktywności nie wystarcza."
            ),
            **self._training_story(sessions, recovery, goal, hard),
            "execution_assessments": {
                key: counts[key] for key in ("on_target", "too_hard", "too_easy", "insufficient_evidence")
            },
            "uncertain_sessions_count": uncertain,
            "positives": positives,
            "attention": attention,
            "next_steps": next_steps,
            "limitations": limitations,
        }

    def _training_story(self, sessions, recovery, goal, hard):
        benefits = []
        # Only well-supported, on-plan sessions justify a positive stimulus claim.
        supported = [s for s in sessions if s["execution_review"]["status"] == "on_target"
                     and s["execution_review"]["confidence"] >= 0.5]
        groups = [
            ({"easy_run", "recovery_run", "easy_run+strides", "easy_run+hills"}, "aerobic",
             "Spokojne biegi wspierały bazę tlenową i ciągłość treningu — fundament utrzymania tempa na 10 km."),
            ({"threshold", "tempo", "tempo_run"}, "threshold",
             "Praca progowa i tempowa dostarczyła bodźca do dłuższego utrzymywania mocnego wysiłku — ważnego na 10 km."),
            ({"intervals", "vo2max"}, "speed_endurance",
             "Interwały dostarczyły bodźca do pracy przy wysokiej intensywności, wspierającego przygotowanie do szybkiego biegu na 10 km."),
            ({"long_run"}, "endurance",
             "Dłuższy bieg wspierał wytrzymałość potrzebną do utrzymania wysiłku także w końcówce dystansu."),
            ({"strength"}, "strength",
             "Trening siłowy wniósł pracę uzupełniającą przygotowania biegowe; sam zapis nie potwierdza jeszcze poprawy ekonomii biegu."),
        ]
        for types, code, text in groups:
            matched = [s for s in supported if s.get("workout_type") in types]
            if matched:
                benefits.append({"code": code, "text": text, "evidence": [
                    f"Sesje zgodne z planem, z pewnością oceny co najmniej 0,5: {len(matched)}.",
                    *[f"{s.get('workout_type')}: {s.get('total_distance_km')} km / {s.get('total_duration_min')} min." for s in matched],
                ]})
        fatigue = recovery["fatigue_signal"]
        if hard >= 2 or fatigue in {"accumulating", "high"}:
            load = "Są sygnały, że obciążenie mogło być zbyt duże. Nie dokładaj intensywności, zanim ponownie ocenisz regenerację. To ostrzeżenie treningowe, nie diagnoza przetrenowania."
        elif hard or fatigue == "watch":
            load = "Pojawił się sygnał ostrzegawczy. Obserwuj odczucia i regenerację przed kolejnym akcentem; pojedyncza trudniejsza sesja nie przesądza o narastającym zmęczeniu."
        elif fatigue == "insufficient_data" or not supported:
            load = "Nie ma wystarczających danych, by wykluczyć zbyt duże obciążenie. Uzupełnij pomiary regeneracji i odczucia po treningach."
        else:
            load = "W dostępnych ocenach nie widać powtarzającego się nadmiernego bodźca ani narastającego sygnału zmęczenia. Nadal obserwuj odczucia — brak ostrzeżenia nie gwarantuje pełnej regeneracji."
        goal_context = None
        if goal and goal.distance_km and goal.target_time_sec:
            minutes, seconds = divmod(goal.target_time_sec, 60)
            pace = round(goal.target_time_sec / goal.distance_km)
            pace_min, pace_sec = divmod(pace, 60)
            goal_context = {
                "label": f"{goal.distance_km:g} km w {minutes}:{seconds:02d}",
                "target_date": goal.target_date.isoformat() if goal.target_date else None,
                "target_pace": f"{pace_min}:{pace_sec:02d}/km",
                "summary": (
                    "Tydzień wniósł pracę wspierającą wymagania celu. Teraz kluczowe jest przyswojenie bodźca; sygnały zmęczenia przemawiają za ochroną regeneracji, a nie przyspieszaniem kolejnych sesji."
                    if benefits and (hard or fatigue in {"watch", "accumulating", "high"}) else
                    "Tydzień wspierał przygotowania przez bodźce opisane powyżej. Ich regularna realizacja i regeneracja tworzą warunki do postępu."
                    if benefits else
                    "Nie ma dość wiarygodnych wykonań, aby powiązać ten tydzień z postępem w kierunku celu. Sprawdź zapisy i oceny sesji."
                ),
                "limitation": "To interpretacja bodźców, nie prognoza wyniku. Jeden tydzień nie potwierdza gotowości startowej ani tego, o ile poprawił się czas na 10 km.",
            }
        return {"training_benefits": benefits, "load_interpretation": load, "goal_context": goal_context}
