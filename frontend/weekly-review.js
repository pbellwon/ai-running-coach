let selectedWeeklyWeek = null;
let currentWeeklyWeek = null;
let weeklyReviewRequest = 0;

function shiftWeeklyDate(isoDate, days) {
    const date = new Date(`${isoDate}T12:00:00Z`);
    date.setUTCDate(date.getUTCDate() + days);
    return date.toISOString().slice(0, 10);
}

function formatWeeklyDate(isoDate) {
    return new Intl.DateTimeFormat("pl-PL", {
        day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
    }).format(new Date(`${isoDate}T12:00:00Z`));
}

function initializeWeeklyReview() {
    const card = document.getElementById("weekly-coach-review-card");
    if (!card || card.dataset.initialized) return;
    card.dataset.initialized = "true";
    document.getElementById("weekly-review-previous").addEventListener("click", () => {
        if (selectedWeeklyWeek) loadWeeklyCoachReview(shiftWeeklyDate(selectedWeeklyWeek, -7));
    });
    document.getElementById("weekly-review-next").addEventListener("click", () => {
        if (selectedWeeklyWeek) loadWeeklyCoachReview(shiftWeeklyDate(selectedWeeklyWeek, 7));
    });
    document.getElementById("weekly-review-current").addEventListener("click", () => {
        if (currentWeeklyWeek) loadWeeklyCoachReview(currentWeeklyWeek);
    });
    document.getElementById("weekly-review-latest").addEventListener("click", () => loadWeeklyCoachReview(null));
    document.getElementById("weekly-review-retry").addEventListener("click", () => loadWeeklyCoachReview());
}

async function loadWeeklyCoachReview(weekStart = selectedWeeklyWeek) {
    const card = document.getElementById("weekly-coach-review-card");
    if (!card) return;
    initializeWeeklyReview();
    selectedWeeklyWeek = weekStart;
    const request = ++weeklyReviewRequest;
    const state = document.getElementById("weekly-review-state");
    const content = document.getElementById("weekly-review-content");
    const retry = document.getElementById("weekly-review-retry");
    const buttons = card.querySelectorAll("nav button");
    buttons.forEach(button => { button.disabled = true; });
    retry.classList.add("hidden");
    content.innerHTML = "";
    card.setAttribute("aria-busy", "true");
    state.textContent = "Wczytywanie przeglądu…";
    try {
        const query = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : "";
        const response = await fetch(`${API_BASE_URL}/review/week${query}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Weekly review returned ${response.status}`);
        const data = await response.json();
        if (request !== weeklyReviewRequest) return;
        selectedWeeklyWeek = data.week_start;
        currentWeeklyWeek = data.current_week_start;
        document.getElementById("weekly-review-period").textContent =
            `${formatWeeklyDate(data.week_start)} – ${formatWeeklyDate(data.week_end)}`;
        state.textContent = data.period_status === "in_progress"
            ? `Tydzień w toku — stan na ${formatWeeklyDate(data.as_of_date)}. Dzisiaj i przyszłe jednostki bez wykonania pozostają w planie.`
            : "Zakończony tydzień";
        renderWeeklyCoachReview(data);
    } catch (error) {
        if (request !== weeklyReviewRequest) return;
        console.error("Could not load weekly review:", error);
        document.getElementById("weekly-review-period").textContent = weekStart
            ? `${formatWeeklyDate(weekStart)} – ${formatWeeklyDate(shiftWeeklyDate(weekStart, 6))}` : "";
        state.textContent = "Nie udało się wczytać przeglądu tygodnia. Pozostałe dane dashboardu są dostępne.";
        retry.classList.remove("hidden");
    } finally {
        if (request === weeklyReviewRequest) {
            card.removeAttribute("aria-busy");
            buttons.forEach(button => { button.disabled = false; });
            document.getElementById("weekly-review-previous").disabled = !selectedWeeklyWeek;
            document.getElementById("weekly-review-next").disabled = !selectedWeeklyWeek
                || !currentWeeklyWeek || selectedWeeklyWeek >= currentWeeklyWeek;
            document.getElementById("weekly-review-current").disabled = !currentWeeklyWeek
                || selectedWeeklyWeek === currentWeeklyWeek;
        }
    }
}

function renderWeeklyCoachReview(data) {
    const coach = data.coach;
    const summary = data.summary;
    const recovery = data.recovery;
    const distribution = data.training_distribution;
    const labels = {
        on_target: "Zgodnie z założeniami", too_hard: "Za duży bodziec", too_easy: "Za mały bodziec",
        insufficient_evidence: "Za mało danych", missed: "Brak zapisu wykonania", pending: "W planie",
        type_matched: "Dopasowano wykonanie", type_mismatch: "Inny typ wykonania", off: "Odpoczynek",
    };
    const fatigueLabels = {
        none: "Bez narastającego sygnału w dostępnych danych", watch: "Obserwuj regenerację",
        accumulating: "Narastające sygnały zmęczenia", high: "Silne sygnały zmęczenia",
        insufficient_data: "Za mało danych do oceny trendu",
    };
    const trendLabels = {
        improving: "poprawa", worsening: "pogorszenie", stable: "stabilnie",
        mixed: "zmienny", insufficient_data: "za mało pomiarów",
    };
    const number = value => value == null ? "—" : new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 1 }).format(value);
    const findings = (title, entries, emptyText) => `
        <section class="weekly-review-findings">
            <h4>${escapeHtml(title)}</h4>
            ${entries.length ? `<ul>${entries.map(entry => `
                <li>${escapeHtml(entry.text)}
                    <details><summary>Na czym opiera się wniosek?</summary>
                        <ul>${entry.evidence.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
                    </details>
                </li>`).join("")}</ul>` : `<p class="muted">${escapeHtml(emptyText)}</p>`}
        </section>`;

    document.getElementById("weekly-review-content").innerHTML = `
        ${data.status === "no_execution_data" ? `<p class="weekly-review-notice">Brak zapisanych wykonań w tym tygodniu. Sprawdź synchronizację; nie oznacza to automatycznie, że treningi zostały opuszczone.</p>` : ""}
        <h3>${escapeHtml(coach.headline)}</h3>
        <p>${escapeHtml(coach.summary)}</p>
        <div class="weekly-review-story">
            ${findings("Co dał ten tydzień treningów?", coach.training_benefits || [], "Brakuje wiarygodnych wykonań, aby wskazać zrealizowane bodźce. To nie oznacza, że trening nie przyniósł korzyści.")}
            <section class="weekly-review-load">
                <h4>Czy coś było za mocno?</h4>
                <p>${escapeHtml(coach.load_interpretation || "Sprawdź oceny wykonania i regenerację poniżej.")}</p>
                <p class="muted">${escapeHtml(fatigueLabels[recovery.fatigue_signal] || recovery.fatigue_signal)}.</p>
                ${findings("Sygnały wymagające uwagi", coach.attention, "W ocenionych danych nie znaleziono dodatkowych sygnałów wymagających uwagi.")}
            </section>
            ${coach.goal_context ? `<section class="weekly-review-goal">
                <h4>Jak to przybliża do celu?</h4>
                <p class="weekly-review-goal-target">${escapeHtml(coach.goal_context.label)} · ${escapeHtml(coach.goal_context.target_pace)}${coach.goal_context.target_date ? ` · ${escapeHtml(formatWeeklyDate(coach.goal_context.target_date))}` : ""}</p>
                <p>${escapeHtml(coach.goal_context.summary)}</p>
                <p class="muted">${escapeHtml(coach.goal_context.limitation)}</p>
            </section>` : `<p class="muted">Brak skonfigurowanego celu czasowego — nie oceniamy związku tygodnia z konkretnym wynikiem.</p>`}
        </div>
        ${findings("Wnioski na kolejny tydzień", coach.next_steps, "Uzupełnij dane przed oceną kolejnego tygodnia.")}
        <p class="muted">To wskazówki do Twojej decyzji. Plan treningowy pozostaje pod Twoją kontrolą.</p>
        <details class="weekly-review-statistics">
        <summary>Statystyki i szczegóły regeneracji</summary>
        <dl class="weekly-review-metrics">
            <div><dt>Zaplanowane jednostki</dt><dd>${number(summary.planned_training_count)}</dd></div>
            <div><dt>Wykonane sesje</dt><dd>${number(summary.executed_sessions_count)}</dd></div>
            <div><dt>Dopasowane do planu</dt><dd>${number(summary.paired_workouts_count)}</dd></div>
            <div><dt>Brak zapisu z minionych dni</dt><dd>${number(summary.missed_workouts_count)}</dd></div>
            <div><dt>Jeszcze w planie</dt><dd>${number(summary.pending_workouts_count)}</dd></div>
            <div><dt>Bieganie</dt><dd>${number(distribution.distance.running_total_km)} km</dd></div>
            <div><dt>Łączny czas treningów</dt><dd>${number(distribution.duration.total_training_min)} min</dd></div>
            <div><dt>Akcenty / siła</dt><dd>${number(distribution.session_counts.quality)} / ${number(distribution.session_counts.strength)}</dd></div>
        </dl>
        <h4>Ocena wykonania</h4>
        <ul class="weekly-review-assessments">${Object.entries(coach.execution_assessments).map(([status, count]) => `
            <li>${escapeHtml(labels[status] || status)}: <strong>${number(count)}</strong></li>`).join("")}
        </ul>
        <p class="muted">Oceny opisują bodziec względem planu; uwzględniają dostępny feedback. Wnioski o trudnościach wymagają pewności oceny co najmniej 0,5.</p>
        <h4>Regeneracja</h4>
        <p>${escapeHtml(fatigueLabels[recovery.fatigue_signal] || recovery.fatigue_signal)}.
            Dane z ${number(recovery.available_days)} dni; brak danych z ${number(recovery.missing_days)} dni.
            Średni sen: ${number(recovery.average_sleep_hours)} h.
        </p>
        <p class="muted">Sygnał na koniec okresu wykorzystuje maksymalnie ${number(recovery.trend.window_days)} ostatnich dni tego tygodnia; dostępne w tym oknie: ${number(recovery.trend.available_days)}.</p>
        <p>Dni z dobrą oceną regeneracji: ${number(recovery.status_counts.good)},
            z ostrożnością: ${number(recovery.status_counts.caution)},
            ze słabą oceną: ${number(recovery.status_counts.poor)}.</p>
        <ul>
            ${[["HRV", "hrv"], ["Tętno spoczynkowe", "resting_hr"], ["Długość snu", "sleep_duration"]].map(([label, metric]) => `
                <li>${escapeHtml(label)} — trend: ${escapeHtml(trendLabels[recovery.trend[metric].direction])}</li>
            `).join("")}
        </ul>
        ${findings("Zgodność z planem", coach.positives, "Za mało dowodów, aby ocenić zgodność z planem.")}
        </details>
        <details class="weekly-review-days">
            <summary>Plan i wykonanie dzień po dniu</summary>
            <div class="weekly-review-table-scroll">
                <table>
                    <caption>Porównanie zaplanowanych jednostek z logicznymi sesjami</caption>
                    <thead><tr><th scope="col">Dzień</th><th scope="col">Plan</th><th scope="col">Wykonanie i ocena</th></tr></thead>
                    <tbody>${data.days.map(day => `<tr>
                        <th scope="row">${escapeHtml(formatWeeklyDate(day.date))}</th>
                        <td>${day.planned_workouts.length ? `<ul>${day.planned_workouts.map(plan => `<li>
                            ${escapeHtml(plan.title)} — ${escapeHtml(labels[plan.match_status] || plan.match_status)}
                        </li>`).join("")}</ul>` : "Brak wpisu w planie"}</td>
                        <td>${day.executed_sessions.length ? `<ul>${day.executed_sessions.map(session => {
                            const review = session.execution_review;
                            return `<li>${escapeHtml(formatWorkoutType(session.workout_type))}: ${number(session.total_distance_km)} km / ${number(session.total_duration_min)} min
                                <br>${escapeHtml(labels[review.status] || review.status)}
                                ${review.confidence < 0.5 ? " (niska pewność oceny)" : ""}
                                <details><summary>Dowody i uwagi</summary><ul>${[...(review.evidence || []), ...(review.warnings || [])].map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul></details>
                            </li>`;
                        }).join("")}</ul>` : "Brak zapisu wykonania"}</td>
                    </tr>`).join("")}</tbody>
                </table>
            </div>
        </details>
        <details class="weekly-review-limitations">
            <summary>Zakres i ograniczenia oceny</summary>
            <ul>${coach.limitations.map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul>
        </details>
    `;
}
