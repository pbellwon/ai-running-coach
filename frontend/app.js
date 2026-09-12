const API_BASE_URL =
    "https://pacemind-backend-1034229547127.europe-central2.run.app";


document.addEventListener(
    "DOMContentLoaded",
    () => {
        loadDashboard();
    }
);


document.addEventListener(
    "DOMContentLoaded",
    () => {
        const refreshButton =
            document.getElementById(
                "refresh-button"
            );

        refreshButton.addEventListener(
            "click",
            () => {
                refreshData();
            }
        );
    }
);


async function loadDashboard() {
    await Promise.all([
        loadToday(),
        loadTrainingOverview(),
        loadRecentWorkouts(),
    ]);
}


async function loadToday() {
    const loadingState =
        document.getElementById(
            "loading-state"
        );

    const errorState =
        document.getElementById(
            "error-state"
        );

    const dashboard =
        document.getElementById(
            "dashboard"
        );

    loadingState.classList.remove(
        "hidden"
    );

    errorState.classList.add(
        "hidden"
    );

    dashboard.classList.add(
        "hidden"
    );

    try {
        const response = await fetch(
            `${API_BASE_URL}/today`
        );

        if (!response.ok) {
            throw new Error(
                `API returned ${response.status}`
            );
        }

        const data =
            await response.json();

        if (
            data.status !== "ready"
            && data.status !== "completed"
            && data.status !== "no_planned_workout"
        ) {
            throw new Error(
                data.message
                || "PaceMind is not ready for today."
            );
        }

        renderToday(data);

        loadingState.classList.add(
            "hidden"
        );

        dashboard.classList.remove(
            "hidden"
        );

    } catch (error) {
        loadingState.classList.add(
            "hidden"
        );

        document.getElementById(
            "error-message"
        ).textContent =
            error.message;

        errorState.classList.remove(
            "hidden"
        );
    }
}


async function loadTrainingOverview() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/training/overview`
        );

        if (!response.ok) {
            throw new Error(
                `Training overview returned ${response.status}`
            );
        }

        const data =
            await response.json();

        renderTrainingOverview(
            data
        );

    } catch (error) {
        console.error(
            "Could not load training overview:",
            error
        );
    }
}


async function refreshData() {
    const refreshButton =
        document.getElementById(
            "refresh-button"
        );

    const originalText =
        refreshButton.textContent;

    refreshButton.disabled = true;
    refreshButton.textContent =
        "Refreshing...";

    try {
        const response = await fetch(
            `${API_BASE_URL}/sync/refresh`,
            {
                method: "POST",
            }
        );

        if (response.status === 429) {
            const data =
                await response.json();

            const seconds =
                data
                    .detail
                    ?.retry_after_seconds
                ?? 0;

            const minutes =
                Math.ceil(
                    seconds / 60
                );

            alert(
                `Data was refreshed recently. Try again in about ${minutes} min.`
            );

            return;
        }

        if (!response.ok) {
            throw new Error(
                `Refresh failed: ${response.status}`
            );
        }

        await loadDashboard();

    } catch (error) {
        alert(
            error.message
            || "Could not refresh data."
        );

    } finally {
        refreshButton.disabled = false;
        refreshButton.textContent =
            originalText;
    }
}


function renderToday(data) {
    renderDate(
        data.target_date
    );

    renderRecovery(
        data
    );

    renderPlan(
        data.planned_workout
    );

    renderTrainingContext(
        data.training_context
    );

    if (
        data.status === "completed"
    ) {
        renderCompleted(
            data
        );

        return;
    }

    if (
        data.status === "no_planned_workout"
    ) {
        renderNoPlannedWorkout(
            data
        );

        return;
    }

    renderRecommendation(
        data.decision,
        data.recommendation
    );

    renderReasons(
        data.recommendation
    );
}


function renderDate(
    dateValue
) {
    const date = new Date(
        `${dateValue}T12:00:00`
    );

    const formatted =
        new Intl.DateTimeFormat(
            "en-GB",
            {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
            }
        ).format(date);

    document.getElementById(
        "today-date"
    ).textContent = formatted;
}


function renderRecovery(
    data
) {
    const recovery =
        data.recovery;

    const trend =
        data.recovery_trend;

    const overallStatus =
        document.getElementById(
            "overall-status"
        );

    const status =
        recovery?.overall_status
        || "unknown";

    overallStatus.textContent =
        formatLabel(
            status
        );

    overallStatus.className =
        `status-badge ${status}`;

    document.getElementById(
        "recovery-title"
    ).textContent =
        formatLabel(
            status
        );

    renderMetric(
        "hrv-value",
        "hrv-baseline",
        recovery?.hrv?.current,
        recovery?.hrv?.baseline,
        null
    );

    renderMetric(
        "rhr-value",
        "rhr-baseline",
        recovery?.resting_hr?.current,
        recovery?.resting_hr?.baseline,
        " bpm"
    );

    const sleepSeconds =
        recovery
            ?.sleep_duration
            ?.current;

    const sleepBaselineSeconds =
        recovery
            ?.sleep_duration
            ?.baseline;

    document.getElementById(
        "sleep-value"
    ).textContent =
        formatSleep(
            sleepSeconds
        );

    const sleepScore =
        recovery
            ?.sleep_score
            ?.current;

    const baselineText =
        sleepBaselineSeconds != null
            ? (
                `baseline ${
                    formatSleep(
                        sleepBaselineSeconds
                    )
                }`
            )
            : "No baseline";

    document.getElementById(
        "sleep-score"
    ).textContent =
        sleepScore != null
            ? (
                `score ${sleepScore}`
                + ` · ${baselineText}`
            )
            : baselineText;

    document.getElementById(
        "fatigue-value"
    ).textContent =
        formatLabel(
            trend?.fatigue_signal
            || "unknown"
        );

    document.getElementById(
        "fatigue-detail"
    ).textContent =
        `${trend?.available_days ?? 0}`
        + ` / ${trend?.window_days ?? 0}`
        + " days";
}


function renderMetric(
    valueElementId,
    baselineElementId,
    current,
    baseline,
    suffix
) {
    document.getElementById(
        valueElementId
    ).textContent =
        current != null
            ? (
                `${current}${
                    suffix || ""
                }`
            )
            : "—";

    document.getElementById(
        baselineElementId
    ).textContent =
        baseline != null
            ? (
                `baseline ${baseline}${
                    suffix || ""
                }`
            )
            : "No baseline";
}


function renderPlan(
    plan
) {
    document.getElementById(
        "plan-title"
    ).textContent =
        plan?.title
        || "No planned workout";

    const summaryParts = [];

    if (
        plan?.planned_distance_km
        != null
    ) {
        summaryParts.push(
            `${plan.planned_distance_km} km`
        );
    }

    if (
        plan?.planned_duration_min
        != null
    ) {
        summaryParts.push(
            `${plan.planned_duration_min} min`
        );
    }

    if (
        plan?.workout_type
    ) {
        summaryParts.push(
            formatWorkoutType(
                plan.workout_type
            )
        );
    }

    document.getElementById(
        "plan-summary"
    ).textContent =
        summaryParts.join(" · ")
        || "No workout planned for today";

    document.getElementById(
        "plan-description"
    ).textContent =
        plan?.description || "";
}


function renderNoPlannedWorkout(
    data
) {
    const recommendationCard =
        document.getElementById(
            "recommendation-card"
        );

    const completedCard =
        document.getElementById(
            "completed-card"
        );

    recommendationCard.classList.add(
        "hidden"
    );

    completedCard.classList.add(
        "hidden"
    );

    renderCurrentRecoveryReasons(
        data
    );
}


function renderRecommendation(
    decision,
    recommendation
) {
    const recommendationCard =
        document.getElementById(
            "recommendation-card"
        );

    const completedCard =
        document.getElementById(
            "completed-card"
        );

    recommendationCard.classList.remove(
        "hidden"
    );

    completedCard.classList.add(
        "hidden"
    );

    const decisionBadge =
        document.getElementById(
            "decision-badge"
        );

    decisionBadge.textContent =
        formatDecision(
            decision.decision
        );

    decisionBadge.className =
        `decision-badge ${decision.decision}`;

    document.getElementById(
        "recommendation-title"
    ).textContent =
        recommendation.title;

    document.getElementById(
        "recommendation-summary"
    ).textContent =
        recommendation.summary;

    const volumeContainer =
        document.getElementById(
            "recommendation-volume"
        );

    volumeContainer.innerHTML = "";

    if (
        recommendation
            .recommended_distance_km
        != null
    ) {
        volumeContainer.appendChild(
            createVolumePill(
                `${recommendation
                    .recommended_distance_km} km`
            )
        );
    }

    if (
        recommendation
            .recommended_duration_min
        != null
    ) {
        volumeContainer.appendChild(
            createVolumePill(
                `${recommendation
                    .recommended_duration_min} min`
            )
        );
    }

    if (
        recommendation
            .recommended_workout_type
    ) {
        volumeContainer.appendChild(
            createVolumePill(
                formatWorkoutType(
                    recommendation
                        .recommended_workout_type
                )
            )
        );
    }
}


function renderCompleted(
    data
) {
    const recommendationCard =
        document.getElementById(
            "recommendation-card"
        );

    const completedCard =
        document.getElementById(
            "completed-card"
        );

    recommendationCard.classList.add(
        "hidden"
    );

    completedCard.classList.remove(
        "hidden"
    );

    const session =
        data
            .training_context
            ?.last_session;

    document.getElementById(
        "completed-title"
    ).textContent =
        data.planned_workout?.title
        || "Workout completed";

    document.getElementById(
        "completed-summary"
    ).textContent =
        data.message
        || "Today's planned workout has been completed.";

    const container =
        document.getElementById(
            "completed-volume"
        );

    container.innerHTML = "";

    if (
        session?.distance_km
        != null
    ) {
        container.appendChild(
            createVolumePill(
                `${session.distance_km} km`
            )
        );
    }

    if (
        session?.duration_min
        != null
    ) {
        container.appendChild(
            createVolumePill(
                `${session.duration_min} min`
            )
        );
    }

    if (
        session?.workout_type
    ) {
        container.appendChild(
            createVolumePill(
                formatWorkoutType(
                    session.workout_type
                )
            )
        );
    }

    renderCurrentRecoveryReasons(
        data
    );
}


function renderCurrentRecoveryReasons(
    data
) {
    const reasonsTitle =
        document.getElementById(
            "reasons-title"
        );

    reasonsTitle.textContent =
        "CURRENT RECOVERY";

    const reasonsList =
        document.getElementById(
            "reasons-list"
        );

    reasonsList.innerHTML = "";

    const items = [
        ...(
            data.recovery?.reasons
            || []
        ),
        ...(
            data.recovery_trend?.reasons
            || []
        ),
    ];

    if (
        items.length === 0
    ) {
        items.push(
            "No material recovery warning detected."
        );
    }

    items.forEach(
        (item) => {
            const li =
                document.createElement(
                    "li"
                );

            li.textContent = item;

            reasonsList.appendChild(
                li
            );
        }
    );
}


function renderReasons(
    recommendation
) {
    const reasonsTitle =
        document.getElementById(
            "reasons-title"
        );

    reasonsTitle.textContent =
        "WHY?";

    const reasonsList =
        document.getElementById(
            "reasons-list"
        );

    reasonsList.innerHTML = "";

    const items = [
        ...(
            recommendation.reasons
            || []
        ),
        ...(
            recommendation.warnings
            || []
        ),
    ];

    if (
        items.length === 0
    ) {
        items.push(
            "No additional explanation available."
        );
    }

    items.forEach(
        (item) => {
            const li =
                document.createElement(
                    "li"
                );

            li.textContent = item;

            reasonsList.appendChild(
                li
            );
        }
    );
}


function renderTrainingContext(
    context
) {
    document.getElementById(
        "context-running"
    ).textContent =
        `${context?.running_distance_km ?? 0} km`;

    document.getElementById(
        "context-running-sessions"
    ).textContent =
        context?.running_sessions ?? 0;

    document.getElementById(
        "context-quality"
    ).textContent =
        context?.quality_sessions ?? 0;

    document.getElementById(
        "context-long"
    ).textContent =
        context?.long_run_sessions ?? 0;

    document.getElementById(
        "context-strength"
    ).textContent =
        context?.strength_sessions ?? 0;

    document.getElementById(
        "context-cross-training"
    ).textContent =
        `${context?.cycling_sessions ?? 0} sessions`;

    document.getElementById(
        "context-total-time"
    ).textContent =
        formatTrainingTime(
            context?.total_training_min
        );
}


function renderTrainingOverview(
    context
) {
    document.getElementById(
        "overview-running"
    ).textContent =
        `${context?.running_distance_km ?? 0} km`;

    document.getElementById(
        "overview-running-sessions"
    ).textContent =
        context?.running_sessions ?? 0;

    document.getElementById(
        "overview-easy"
    ).textContent =
        context?.easy_sessions ?? 0;

    document.getElementById(
        "overview-quality"
    ).textContent =
        context?.quality_sessions ?? 0;

    document.getElementById(
        "overview-long"
    ).textContent =
        context?.long_run_sessions ?? 0;

    document.getElementById(
        "overview-strength"
    ).textContent =
        context?.strength_sessions ?? 0;

    document.getElementById(
        "overview-cross-training"
    ).textContent =
        `${context?.cycling_sessions ?? 0} sessions`;

    document.getElementById(
        "overview-total-time"
    ).textContent =
        formatTrainingTime(
            context?.total_training_min
        );
}


async function loadRecentWorkouts() {
    const container =
        document.getElementById(
            "recent-workouts-list"
        );

    if (!container) {
        return;
    }

    container.innerHTML = `
        <p class="recent-workouts-state">
            Loading recent workouts...
        </p>
    `;

    try {
        const response = await fetch(
            `${API_BASE_URL}/workouts/recent-reviews?limit=3`
        );

        if (!response.ok) {
            throw new Error(
                `Recent workouts returned ${response.status}`
            );
        }

        const data =
            await response.json();

        renderRecentWorkouts(
            data.items || []
        );

    } catch (error) {
        console.error(
            "Could not load recent workouts:",
            error
        );

        container.innerHTML = `
            <p class="recent-workouts-state recent-workouts-error">
                Recent workouts are unavailable.
            </p>
        `;
    }
}


function renderRecentWorkouts(
    items
) {
    const container =
        document.getElementById(
            "recent-workouts-list"
        );

    container.innerHTML = "";

    if (
        !items
        || items.length === 0
    ) {
        container.innerHTML = `
            <p class="recent-workouts-state">
                No recent workouts available.
            </p>
        `;

        return;
    }

    items.forEach(
        (item) => {
            container.appendChild(
                createRecentWorkoutCard(
                    item
                )
            );
        }
    );
}


function createRecentWorkoutCard(
    item
) {
    const row =
        document.createElement(
            "article"
        );

    row.className =
        "recent-workout";

    const header =
        document.createElement(
            "div"
        );

    header.className =
        "recent-workout-header";

    const titleBlock =
        document.createElement(
            "div"
        );

    const dateElement =
        document.createElement(
            "p"
        );

    dateElement.className =
        "recent-workout-date";

    dateElement.textContent =
        formatRecentWorkoutDate(
            item.date
        );

    const title =
        document.createElement(
            "h3"
        );

    title.className =
        "recent-workout-title";

    title.textContent =
        item.planned_workout?.title
        || formatWorkoutType(
            item.workout_type
        );

    titleBlock.appendChild(
        dateElement
    );

    titleBlock.appendChild(
        title
    );

    const status =
        document.createElement(
            "span"
        );

    const reviewStatus =
        item.review?.status
        || "insufficient_evidence";

    status.className =
        `execution-badge ${reviewStatus}`;

    status.textContent =
        formatExecutionStatus(
            reviewStatus
        );

    header.appendChild(
        titleBlock
    );

    header.appendChild(
        status
    );

    const details =
        document.createElement(
            "div"
        );

    details.className =
        "recent-workout-details";

    const executedType =
        createRecentWorkoutDetail(
            "Executed",
            formatWorkoutType(
                item.workout_type
            )
        );

    details.appendChild(
        executedType
    );

    if (
        item.distance_km != null
    ) {
        details.appendChild(
            createRecentWorkoutDetail(
                "Distance",
                `${formatNumber(
                    item.distance_km
                )} km`
            )
        );
    }

    if (
        item.duration_min != null
    ) {
        details.appendChild(
            createRecentWorkoutDetail(
                "Duration",
                `${formatNumber(
                    item.duration_min
                )} min`
            )
        );
    }

    const planSummary =
        buildRecentPlanSummary(
            item
        );

    if (planSummary) {
        details.appendChild(
            createRecentWorkoutDetail(
                "Plan",
                planSummary
            )
        );
    }

    row.appendChild(
        header
    );

    row.appendChild(
        details
    );

    return row;
}


function createRecentWorkoutDetail(
    label,
    value
) {
    const element =
        document.createElement(
            "div"
        );

    element.className =
        "recent-workout-detail";

    const labelElement =
        document.createElement(
            "span"
        );

    labelElement.textContent =
        label;

    const valueElement =
        document.createElement(
            "strong"
        );

    valueElement.textContent =
        value;

    element.appendChild(
        labelElement
    );

    element.appendChild(
        valueElement
    );

    return element;
}


function buildRecentPlanSummary(
    item
) {
    if (!item.planned_workout) {
        return "No matched plan";
    }

    const parts = [];

    if (
        item.review?.planned_distance_km
        != null
    ) {
        parts.push(
            `${formatNumber(
                item.review
                    .planned_distance_km
            )} km`
        );
    }

    if (
        item.review?.planned_duration_min
        != null
    ) {
        parts.push(
            `${formatNumber(
                item.review
                    .planned_duration_min
            )} min`
        );
    }

    return parts.join(" · ");
}


function formatRecentWorkoutDate(
    value
) {
    if (!value) {
        return "Unknown date";
    }

    const date =
        new Date(
            `${value}T12:00:00`
        );

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            weekday: "short",
            day: "numeric",
            month: "short",
        }
    ).format(date);
}


function formatExecutionStatus(
    value
) {
    const labels = {
        on_target:
            "On target",

        too_easy:
            "Easier than planned",

        too_hard:
            "Harder than planned",

        insufficient_evidence:
            "Not enough evidence",
    };

    return (
        labels[value]
        || formatLabel(
            value
        )
    );
}


function formatNumber(
    value
) {
    if (
        value == null
        || Number.isNaN(
            Number(value)
        )
    ) {
        return "—";
    }

    const number =
        Number(value);

    return Number.isInteger(number)
        ? String(number)
        : number.toFixed(1);
}


function formatTrainingTime(
    minutes
) {
    if (
        minutes == null
    ) {
        return "—";
    }

    const totalMinutes =
        Math.round(
            minutes
        );

    const hours =
        Math.floor(
            totalMinutes / 60
        );

    const remainingMinutes =
        totalMinutes % 60;

    return (
        `${hours}h ${
            String(
                remainingMinutes
            ).padStart(
                2,
                "0"
            )
        }m`
    );
}


function createVolumePill(
    text
) {
    const element =
        document.createElement(
            "span"
        );

    element.className =
        "volume-pill";

    element.textContent =
        text;

    return element;
}


function formatSleep(
    seconds
) {
    if (
        seconds == null
    ) {
        return "—";
    }

    const totalMinutes =
        Math.round(
            seconds / 60
        );

    const hours =
        Math.floor(
            totalMinutes / 60
        );

    const minutes =
        totalMinutes % 60;

    return (
        `${hours}h ${
            String(
                minutes
            ).padStart(
                2,
                "0"
            )
        }m`
    );
}


function formatLabel(
    value
) {
    if (
        !value
    ) {
        return "Unknown";
    }

    return value
        .replaceAll(
            "_",
            " "
        )
        .replace(
            /\b\w/g,
            (letter) =>
                letter.toUpperCase()
        );
}


function formatWorkoutType(
    value
) {
    if (
        !value
    ) {
        return "Unknown";
    }

    const labels = {
        easy_run:
            "Easy Run",

        "easy_run+strides":
            "Easy + Strides",

        "easy_run+hills":
            "Easy + Hills",

        threshold:
            "Threshold",

        tempo_run:
            "Tempo",

        vo2max:
            "VO₂max",

        long_run:
            "Long Run",

        "long_run+progression":
            "Long Run + Progression",

        strength:
            "Strength",

        bike:
            "Bike",

        race:
            "Race",
    };

    return (
        labels[value]
        || formatLabel(
            value
        )
    );
}


function formatDecision(
    value
) {
    const labels = {
        do_as_planned:
            "Do as planned",

        reduce:
            "Reduce",

        easy_only:
            "Easy only",

        rest:
            "Rest",
    };

    return (
        labels[value]
        || formatLabel(
            value
        )
    );
}