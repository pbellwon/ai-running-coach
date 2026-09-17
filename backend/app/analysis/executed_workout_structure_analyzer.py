from statistics import mean, median

from app.db.database import SessionLocal
from app.db.models import LapDB


class ExecutedWorkoutStructureAnalyzer:

    FAST_FINISH_MIN_LEAD_IN_KM = 5.0

    FAST_FINISH_MIN_LAP_DISTANCE_M = 800
    FAST_FINISH_MAX_LAP_DISTANCE_M = 1200

    FAST_FINISH_MIN_PACE_IMPROVEMENT = 0.12

    def analyze(
        self,
        workout_file: str,
    ) -> dict:

        db = SessionLocal()

        try:
            laps = (
                db.query(LapDB)
                .filter(
                    LapDB.workout_file
                    == workout_file
                )
                .order_by(
                    LapDB.lap_number.asc()
                )
                .all()
            )

        finally:
            db.close()

        if not laps:
            return {
                "workout_file":
                    workout_file,

                "segments": [],

                "summary": {
                    "laps_count": 0,

                    "detected_type":
                        "unknown",

                    "confidence":
                        0.2,

                    "classification_method":
                        "lap_pattern",

                    "fast_finish": {
                        "detected":
                            False,
                    },

                    "warnings": [
                        (
                            "No laps found "
                            "for this workout."
                        ),
                    ],
                },
            }

        fast_finish = (
            self._detect_fast_finish(
                laps
            )
        )

        continuous_tempo_blocks = (
            self._find_continuous_tempo_blocks(
                laps
            )
        )

        threshold_blocks = (
            self._find_threshold_blocks(
                laps
            )
        )

        tempo_block_lap_numbers = {
            lap.lap_number

            for block
            in continuous_tempo_blocks

            for lap
            in block
        }

        threshold_block_lap_numbers = {
            lap.lap_number

            for block
            in threshold_blocks

            for lap
            in block
        }

        fast_finish_lap_numbers = set(
            fast_finish.get(
                "lap_numbers",
                [],
            )
        )

        easy_laps = []
        stride_laps = []
        recovery_laps = []
        tempo_laps = []
        threshold_laps = []
        vo2max_laps = []
        hill_candidate_laps = []

        for lap in laps:

            if (
                lap.lap_number
                in threshold_block_lap_numbers
            ):
                continue

            if (
                lap.lap_number
                in tempo_block_lap_numbers
            ):
                continue

            if (
                lap.lap_number
                in fast_finish_lap_numbers
            ):
                continue

            distance_m = (
                lap.distance_m
                or 0
            )

            duration_sec = (
                lap.elapsed_time_sec
                or 0
            )

            if (
                distance_m <= 0
                or duration_sec <= 0
            ):
                continue

            pace_sec_per_km = (
                duration_sec
                / (
                    distance_m
                    / 1000
                )
            )

            avg_hr = (
                lap.avg_hr
                or 0
            )

            if (
                70
                <= distance_m
                <= 150
                and 10
                <= duration_sec
                <= 35
            ):
                stride_laps.append(
                    lap
                )

            elif (
                45
                <= duration_sec
                <= 180
                and 150
                <= distance_m
                <= 800
                and pace_sec_per_km
                <= 270
            ):
                vo2max_laps.append(
                    lap
                )

            elif (
                20
                <= duration_sec
                <= 120
                and 50
                <= distance_m
                <= 400
                and avg_hr
                >= 145
                and pace_sec_per_km
                <= 330
            ):
                hill_candidate_laps.append(
                    lap
                )

            elif (
                180
                <= duration_sec
                <= 720
                and pace_sec_per_km
                <= 255
            ):
                threshold_laps.append(
                    lap
                )

            elif (
                360
                <= duration_sec
                <= 1200
                and pace_sec_per_km
                <= 285
            ):
                tempo_laps.append(
                    lap
                )

            elif (
                70
                <= distance_m
                <= 500
                and pace_sec_per_km
                >= 330
            ):
                recovery_laps.append(
                    lap
                )

            elif (
                distance_m
                >= 800
                and pace_sec_per_km
                >= 270
            ):
                easy_laps.append(
                    lap
                )

        segments = []

        if easy_laps:
            segments.append(
                self._build_distance_segment(
                    segment="easy_block",
                    laps=easy_laps,
                    intensity="easy",
                )
            )

        for tempo_block in (
            continuous_tempo_blocks
        ):
            segments.append(
                self._build_distance_segment(
                    segment="tempo_block",
                    laps=tempo_block,
                    intensity="tempo",
                )
            )

        if tempo_laps:
            segments.append(
                self._build_rep_segment(
                    segment="tempo_reps",
                    laps=tempo_laps,
                    intensity="tempo",
                    distance_unit="km",
                )
            )

        if threshold_blocks:
            segments.append(
                self._build_threshold_block_segment(
                    threshold_blocks
                )
            )

        if threshold_laps:
            segments.append(
                self._build_rep_segment(
                    segment=(
                        "threshold_reps"
                    ),
                    laps=threshold_laps,
                    intensity="threshold",
                    distance_unit="km",
                )
            )

        if vo2max_laps:
            segments.append(
                self._build_rep_segment(
                    segment="vo2max_reps",
                    laps=vo2max_laps,
                    intensity="vo2max",
                    distance_unit="m",
                )
            )

        if hill_candidate_laps:
            segments.append(
                self._build_rep_segment(
                    segment=(
                        "hill_reps_candidate"
                    ),
                    laps=(
                        hill_candidate_laps
                    ),
                    intensity=(
                        "hills_candidate"
                    ),
                    distance_unit="m",
                )
            )

        if stride_laps:
            segments.append(
                self._build_rep_segment(
                    segment="strides",
                    laps=stride_laps,
                    intensity="strides",
                    distance_unit="m",
                )
            )

        if recovery_laps:
            segments.append(
                self._build_rep_segment(
                    segment="recoveries",
                    laps=recovery_laps,
                    intensity="recovery",
                    distance_unit="m",
                )
            )

        if fast_finish.get(
            "detected"
        ):
            segments.append(
                {
                    "segment":
                        "fast_finish",

                    "laps":
                        fast_finish[
                            "laps"
                        ],

                    "distance_km":
                        fast_finish[
                            "distance_km"
                        ],

                    "duration_min":
                        fast_finish[
                            "duration_min"
                        ],

                    "avg_pace_sec_per_km":
                        fast_finish[
                            "avg_pace_sec_per_km"
                        ],

                    "avg_hr":
                        fast_finish[
                            "avg_hr"
                        ],

                    "intensity":
                        "fast_finish",
                }
            )

        detected_type = (
            self._detected_type(
                easy_laps=easy_laps,
                tempo_blocks=(
                    continuous_tempo_blocks
                ),
                tempo_laps=tempo_laps,
                threshold_blocks=(
                    threshold_blocks
                ),
                threshold_laps=(
                    threshold_laps
                ),
                vo2max_laps=(
                    vo2max_laps
                ),
                hill_candidate_laps=(
                    hill_candidate_laps
                ),
                stride_laps=(
                    stride_laps
                ),
                fast_finish=(
                    fast_finish
                ),
            )
        )

        classification = (
            self._classification_summary(
                detected_type=(
                    detected_type
                ),
                tempo_blocks=(
                    continuous_tempo_blocks
                ),
                tempo_laps=(
                    tempo_laps
                ),
                threshold_laps=(
                    threshold_laps
                ),
                vo2max_laps=(
                    vo2max_laps
                ),
                hill_candidate_laps=(
                    hill_candidate_laps
                ),
                fast_finish=(
                    fast_finish
                ),
            )
        )

        return {
            "workout_file":
                workout_file,

            "segments":
                segments,

            "summary": {
                "laps_count":
                    len(laps),

                "detected_type":
                    detected_type,

                "confidence":
                    classification[
                        "confidence"
                    ],

                "classification_method":
                    classification[
                        "classification_method"
                    ],

                "fast_finish":
                    fast_finish,

                "warnings":
                    classification[
                        "warnings"
                    ],
            },
        }

    def _detect_fast_finish(
        self,
        laps,
    ) -> dict:
        """
        Detects a meaningful fast finish after a substantial
        predominantly easy lead-in.

        Short trailing partial laps are ignored. The detector
        evaluates the final full-sized lap instead.
        """

        default_result = {
            "detected": False,
        }

        valid_laps = [
            lap
            for lap in laps
            if (
                lap.distance_m
                and lap.elapsed_time_sec
                and lap.distance_m > 0
                and lap.elapsed_time_sec > 0
            )
        ]

        if len(valid_laps) < 2:
            return default_result

        candidate_index = None

        for index in range(
            len(valid_laps) - 1,
            -1,
            -1,
        ):
            distance_m = (
                valid_laps[index].distance_m
                or 0
            )

            if (
                self.FAST_FINISH_MIN_LAP_DISTANCE_M
                <= distance_m
                <= self.FAST_FINISH_MAX_LAP_DISTANCE_M
            ):
                candidate_index = index
                break

        if candidate_index is None:
            return default_result

        final_lap = (
            valid_laps[candidate_index]
        )

        preceding_laps = (
            valid_laps[:candidate_index]
        )

        if not preceding_laps:
            return default_result

        preceding_distance_km = (
            sum(
                lap.distance_m
                or 0
                for lap in preceding_laps
            )
            / 1000
        )

        if (
            preceding_distance_km
            < self.FAST_FINISH_MIN_LEAD_IN_KM
        ):
            return default_result

        comparable_preceding_laps = [
            lap
            for lap in preceding_laps
            if (
                self.FAST_FINISH_MIN_LAP_DISTANCE_M
                <= (
                    lap.distance_m
                    or 0
                )
                <= self.FAST_FINISH_MAX_LAP_DISTANCE_M
            )
        ]

        if (
            len(
                comparable_preceding_laps
            )
            < 3
        ):
            return default_result

        preceding_paces = [
            (
                lap.elapsed_time_sec
                / (
                    lap.distance_m
                    / 1000
                )
            )
            for lap
            in comparable_preceding_laps
        ]

        baseline_pace = float(
            median(
                preceding_paces
            )
        )

        if baseline_pace <= 0:
            return default_result

        final_distance_m = (
            final_lap.distance_m
            or 0
        )

        final_pace = (
            final_lap.elapsed_time_sec
            / (
                final_distance_m
                / 1000
            )
        )

        pace_improvement = (
            baseline_pace
            - final_pace
        ) / baseline_pace

        if (
            pace_improvement
            < self.FAST_FINISH_MIN_PACE_IMPROVEMENT
        ):
            return default_result

        final_hr = (
            round(
                float(
                    final_lap.avg_hr
                ),
                1,
            )
            if final_lap.avg_hr
            is not None
            else None
        )

        trailing_partial_distance_km = (
            sum(
                lap.distance_m
                or 0
                for lap
                in valid_laps[
                    candidate_index + 1:
                ]
            )
            / 1000
        )

        return {
            "detected": True,
            "laps": 1,
            "lap_numbers": [
                final_lap.lap_number
            ],
            "distance_km": round(
                final_distance_m
                / 1000,
                2,
            ),
            "duration_min": round(
                final_lap.elapsed_time_sec
                / 60,
                1,
            ),
            "avg_pace_sec_per_km": round(
                final_pace,
                1,
            ),
            "avg_hr": final_hr,
            "preceding_easy_distance_km": round(
                preceding_distance_km,
                2,
            ),
            "preceding_median_pace_sec_per_km": round(
                baseline_pace,
                1,
            ),
            "pace_improvement_percent": round(
                pace_improvement
                * 100,
                1,
            ),
            "trailing_partial_distance_km": round(
                trailing_partial_distance_km,
                2,
            ),
        }
    def _find_threshold_blocks(
        self,
        laps: list[LapDB],
    ) -> list[list[LapDB]]:

        min_total_sec = 480
        max_total_sec = 720

        min_work_sec = 60
        max_work_sec = 360

        max_work_pace_sec_per_km = 270

        max_technical_split_sec = 5

        blocks = []
        current_block = []
        work_laps_count = 0

        for lap in laps:

            distance_m = (
                lap.distance_m
                or 0
            )

            duration_sec = (
                lap.elapsed_time_sec
                or 0
            )

            if (
                distance_m <= 0
                or duration_sec <= 0
            ):
                continue

            pace_sec_per_km = (
                duration_sec
                / (
                    distance_m
                    / 1000
                )
            )

            is_technical_split = (
                duration_sec
                <= max_technical_split_sec
            )

            is_threshold_work_fragment = (
                min_work_sec
                <= duration_sec
                <= max_work_sec
                and pace_sec_per_km
                <= max_work_pace_sec_per_km
            )

            if is_threshold_work_fragment:
                current_block.append(
                    lap
                )

                work_laps_count += 1

                continue

            if (
                is_technical_split
                and current_block
            ):
                current_block.append(
                    lap
                )

                continue

            if current_block:
                self._append_threshold_block_if_valid(
                    blocks=blocks,
                    block=current_block,
                    work_laps_count=(
                        work_laps_count
                    ),
                    min_total_sec=(
                        min_total_sec
                    ),
                    max_total_sec=(
                        max_total_sec
                    ),
                )

            current_block = []
            work_laps_count = 0

        if current_block:
            self._append_threshold_block_if_valid(
                blocks=blocks,
                block=current_block,
                work_laps_count=(
                    work_laps_count
                ),
                min_total_sec=(
                    min_total_sec
                ),
                max_total_sec=(
                    max_total_sec
                ),
            )

        return blocks


    def _append_threshold_block_if_valid(
        self,
        blocks: list[list[LapDB]],
        block: list[LapDB],
        work_laps_count: int,
        min_total_sec: int,
        max_total_sec: int,
    ) -> None:

        if work_laps_count < 2:
            return

        total_duration_sec = sum(
            lap.elapsed_time_sec
            or 0
            for lap in block
        )

        if (
            min_total_sec
            <= total_duration_sec
            <= max_total_sec
        ):
            blocks.append(
                list(block)
            )
            
    def _find_continuous_tempo_blocks(
        self,
        laps: list[LapDB],
    ) -> list[list[LapDB]]:

        blocks = []
        current_block = []

        for lap in laps:

            distance_m = (
                lap.distance_m
                or 0
            )

            duration_sec = (
                lap.elapsed_time_sec
                or 0
            )

            avg_hr = (
                lap.avg_hr
                or 0
            )

            if (
                distance_m <= 0
                or duration_sec <= 0
            ):
                continue

            pace_sec_per_km = (
                duration_sec
                / (
                    distance_m
                    / 1000
                )
            )

            is_tempo_km_lap = (
                850
                <= distance_m
                <= 1100
                and pace_sec_per_km
                <= 275
                and avg_hr
                >= 155
            )

            if is_tempo_km_lap:
                current_block.append(
                    lap
                )

            else:
                if (
                    len(
                        current_block
                    )
                    >= 3
                ):
                    blocks.append(
                        current_block
                    )

                current_block = []

        if (
            len(
                current_block
            )
            >= 3
        ):
            blocks.append(
                current_block
            )

        return blocks

    def _build_distance_segment(
        self,
        segment: str,
        laps: list[LapDB],
        intensity: str | None = None,
    ) -> dict:

        result = {
            "segment":
                segment,

            "laps":
                len(laps),

            "distance_km":
                round(
                    sum(
                        (
                            lap.distance_m
                            or 0
                        )
                        for lap
                        in laps
                    )
                    / 1000,
                    2,
                ),

            "duration_min":
                round(
                    sum(
                        (
                            lap.elapsed_time_sec
                            or 0
                        )
                        for lap
                        in laps
                    )
                    / 60,
                    1,
                ),

            "avg_hr":
                self._avg_hr(
                    laps
                ),

            "avg_pace_sec_per_km":
                self._avg_pace(
                    laps
                ),
        }

        if intensity:
            result[
                "intensity"
            ] = intensity

        return result

    def _build_threshold_block_segment(
        self,
        blocks: list[list[LapDB]],
    ) -> dict:

        block_durations = []
        block_distances = []
        block_paces = []
        block_hrs = []

        for block in blocks:

            total_duration_sec = sum(
                lap.elapsed_time_sec
                or 0
                for lap in block
            )

            total_distance_m = sum(
                lap.distance_m
                or 0
                for lap in block
            )

            block_durations.append(
                total_duration_sec
            )

            block_distances.append(
                total_distance_m
            )

            if total_distance_m > 0:
                block_paces.append(
                    total_duration_sec
                    / (
                        total_distance_m
                        / 1000
                    )
                )

            hr_values = [
                lap.avg_hr
                for lap in block
                if lap.avg_hr
            ]

            if hr_values:
                block_hrs.append(
                    mean(
                        hr_values
                    )
                )

        return {
            "segment":
                "threshold_blocks",

            "repetitions":
                len(blocks),

            "avg_duration_sec":
                round(
                    mean(
                        block_durations
                    ),
                    1,
                ),

            "avg_distance_km":
                round(
                    mean(
                        block_distances
                    )
                    / 1000,
                    2,
                ),

            "avg_pace_sec_per_km":
                (
                    round(
                        mean(
                            block_paces
                        ),
                        1,
                    )
                    if block_paces
                    else None
                ),

            "avg_hr":
                (
                    round(
                        mean(
                            block_hrs
                        ),
                        1,
                    )
                    if block_hrs
                    else None
                ),

            "intensity":
                "threshold",
        }


    def _build_rep_segment(
        self,
        segment: str,
        laps: list[LapDB],
        intensity: str,
        distance_unit: str,
    ) -> dict:

        result = {
            "segment":
                segment,

            "repetitions":
                len(laps),

            "avg_duration_sec":
                self._avg_duration(
                    laps
                ),

            "avg_pace_sec_per_km":
                self._avg_pace(
                    laps
                ),

            "avg_hr":
                self._avg_hr(
                    laps
                ),

            "intensity":
                intensity,
        }

        avg_distance_m = (
            self._avg_distance_m(
                laps
            )
        )

        if (
            distance_unit
            == "km"
        ):
            result[
                "avg_distance_km"
            ] = round(
                avg_distance_m
                / 1000,
                2,
            )

        else:
            result[
                "avg_distance_m"
            ] = round(
                avg_distance_m,
                1,
            )

        return result

    def _classification_summary(
        self,
        detected_type: str,
        tempo_blocks: list[list[LapDB]],
        tempo_laps: list[LapDB],
        threshold_laps: list[LapDB],
        vo2max_laps: list[LapDB],
        hill_candidate_laps: list[LapDB],
        fast_finish: dict,
    ) -> dict:

        warnings = [
            (
                "Classification based only "
                "on executed lap pattern."
            ),
        ]

        confidence = 0.55

        classification_method = (
            "lap_pattern"
        )

        if (
            detected_type
            == "unknown"
        ):
            confidence = 0.2

            warnings.append(
                (
                    "Workout type could not "
                    "be classified from laps."
                )
            )

        elif (
            detected_type
            == "easy_run"
        ):
            confidence = 0.65

        elif (
            detected_type
            == "easy_run+strides"
        ):
            confidence = 0.75

        elif (
            detected_type
            == "tempo_run"
        ):
            confidence = 0.65

            if tempo_blocks:
                confidence = 0.7

                warnings.append(
                    (
                        "Tempo block detected "
                        "from consecutive similar laps."
                    )
                )

            if tempo_laps:
                warnings.append(
                    (
                        "Tempo repetitions detected "
                        "from lap duration and pace."
                    )
                )

        elif (
            detected_type
            == "threshold"
        ):
            confidence = 0.6

            warnings.append(
                (
                    "Threshold classification is "
                    "estimated from pace and duration."
                )
            )

        elif (
            detected_type
            == "threshold+vo2max"
        ):
            confidence = 0.65

            warnings.append(
                (
                    "Composite workout classification "
                    "is estimated from mixed lap patterns."
                )
            )

        elif (
            detected_type
            == "vo2max"
        ):
            confidence = 0.6

            warnings.append(
                (
                    "VO2max classification is "
                    "estimated from short fast repetitions."
                )
            )

        elif (
            detected_type
            == "hills_candidate"
        ):
            confidence = 0.45

            warnings.append(
                (
                    "Hills cannot be confirmed without "
                    "elevation or planned workout context."
                )
            )

        if hill_candidate_laps:
            warnings.append(
                (
                    "Hill candidates should be verified "
                    "with elevation or planned workout data."
                )
            )

        if fast_finish.get(
            "detected"
        ):
            warnings.append(
                (
                    "Fast finish detected after "
                    "a substantial easier lead-in."
                )
            )

        return {
            "confidence":
                confidence,

            "classification_method":
                classification_method,

            "warnings":
                warnings,
        }

    def _avg_hr(
        self,
        laps: list[LapDB],
    ):

        values = [
            lap.avg_hr
            for lap in laps
            if lap.avg_hr
        ]

        if not values:
            return None

        return round(
            mean(
                values
            ),
            1,
        )

    def _avg_duration(
        self,
        laps: list[LapDB],
    ):

        values = [
            lap.elapsed_time_sec
            for lap in laps
            if lap.elapsed_time_sec
        ]

        if not values:
            return None

        return round(
            mean(
                values
            ),
            1,
        )

    def _avg_distance_m(
        self,
        laps: list[LapDB],
    ):

        values = [
            lap.distance_m
            for lap in laps
            if lap.distance_m
        ]

        if not values:
            return 0

        return mean(
            values
        )

    def _avg_pace(
        self,
        laps: list[LapDB],
    ):

        values = [
            (
                lap.elapsed_time_sec
                / (
                    lap.distance_m
                    / 1000
                )
            )
            for lap in laps
            if (
                lap.distance_m
                and lap.elapsed_time_sec
            )
        ]

        if not values:
            return None

        return round(
            mean(
                values
            ),
            1,
        )

    def _detected_type(
        self,
        easy_laps: list[LapDB],
        tempo_blocks: list[list[LapDB]],
        tempo_laps: list[LapDB],
        threshold_blocks: list[list[LapDB]],
        threshold_laps: list[LapDB],
        vo2max_laps: list[LapDB],
        hill_candidate_laps: list[LapDB],
        stride_laps: list[LapDB],
        fast_finish: dict,
    ) -> str:

        if (
            fast_finish.get(
                "detected"
            )
            and easy_laps
        ):
            if stride_laps:
                return (
                    "easy_run+strides"
                )

            return "easy_run"

        if (
            threshold_blocks
            and vo2max_laps
        ):
            return (
                "threshold+vo2max"
            )

        if (
            threshold_laps
            and vo2max_laps
        ):
            return (
                "threshold+vo2max"
            )

        if (
            tempo_blocks
            or tempo_laps
        ):
            return "tempo_run"

        if threshold_blocks:
            return "threshold"

        if threshold_laps:
            return "threshold"

        if vo2max_laps:
            return "vo2max"

        if hill_candidate_laps:
            return (
                "hills_candidate"
            )

        if (
            easy_laps
            and stride_laps
        ):
            return (
                "easy_run+strides"
            )

        if easy_laps:
            return "easy_run"

        if stride_laps:
            return "fast_reps"

        return "unknown"