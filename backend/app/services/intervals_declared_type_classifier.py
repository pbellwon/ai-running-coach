from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass
class DeclaredWorkoutClassification:
    workout_type: str | None
    session_role: str | None


class IntervalsDeclaredTypeClassifier:
    """
    Extracts two independent dimensions from activity metadata:

    workout_type:
        physiological / execution character
        e.g. easy_run, threshold, tempo_run, intervals

    session_role:
        role in the training structure
        e.g. long_run

    Example:
        "Long tempo"

        workout_type = tempo_run
        session_role = long_run
    """

    def classify(
        self,
        name: str | None,
        description: str | None = None,
        race: bool | None = None,
        external_type: str | None = None,
    ) -> DeclaredWorkoutClassification:

        text = self._normalize(
            " ".join(
                value
                for value in (
                    name,
                    description,
                )
                if value
            )
        )

        session_role = self._classify_role(
            text=text,
        )

        workout_type = self._classify_workout_type(
            text=text,
            race=race,
            external_type=external_type,
        )

        return DeclaredWorkoutClassification(
            workout_type=workout_type,
            session_role=session_role,
        )

    def _classify_role(
        self,
        text: str,
    ) -> str | None:

        if not text:
            return None

        if (
            self._contains_any(
                text,
                {
                    "long run",
                    "longrun",
                    "dlugi bieg",
                    "dlugie wybieganie",
                    "wybieganie",
                },
            )
            or self._has_token(
                text,
                "long",
            )
        ):
            return "long_run"

        return None

    def _classify_workout_type(
        self,
        text: str,
        race: bool | None,
        external_type: str | None,
    ) -> str | None:

        if race is True:
            return "race"

        if self._contains_any(
            text,
            {
                "parkrun",
                "race",
                "wyscig",
                "zawody",
                "test 5k",
                "test 10k",
            },
        ):
            return "race"

        if self._contains_any(
            text,
            {
                "threshold",
                "treshold",
                "progowy",
                "tempo progowe",
            },
        ):
            return "threshold"

        if self._contains_any(
            text,
            {
                "vo2max",
                "vo2 max",
                "vo2",
            },
        ):
            return "vo2max"

        if self._looks_like_intervals(text):
            return "intervals"

        if self._contains_any(
            text,
            {
                "tempo run",
                "tempo",
                "steady",
            },
        ):
            return "tempo_run"

        easy = self._contains_any(
            text,
            {
                "easy",
                "easy run",
                "spokojny",
                "spokojne",
                "rozbieganie",
                "recovery",
                "regeneracyjny",
            },
        )

        strides = self._contains_any(
            text,
            {
                "strides",
                "stride",
                "rytmy",
                "przebiezki",
            },
        )

        hills = self._contains_any(
            text,
            {
                "hill",
                "hills",
                "podbiegi",
            },
        )

        if easy and strides:
            return "easy_run+strides"

        if easy and hills:
            return "easy_run+hills"

        if self._contains_any(
            text,
            {
                "recovery",
                "regeneracyjny",
                "regeneracja",
            },
        ):
            return "recovery_run"

        if easy:
            return "easy_run"

        return self._classify_non_running_type(
            external_type
        )

    def _classify_non_running_type(
        self,
        external_type: str | None,
    ) -> str | None:

        normalized_type = self._normalize(
            external_type or ""
        )

        mapping = {
            "weighttraining": "strength",
            "weight training": "strength",
            "workout": "strength",

            "ride": "bike",
            "virtualride": "bike",
            "virtual ride": "bike",

            "swim": "swimming",
            "walk": "walking",
            "hike": "hiking",
        }

        return mapping.get(normalized_type)

    def _looks_like_intervals(
        self,
        text: str,
    ) -> bool:

        patterns = (
            r"\b\d+\s*x\s*\d+",
            r"\binterwaly\b",
            r"\bintervals\b",
            r"\brepetitions\b",
            r"\breps\b",
        )

        return any(
            re.search(pattern, text)
            for pattern in patterns
        )

    def _has_token(
        self,
        text: str,
        token: str,
    ) -> bool:
        return token in text.split()

    def _contains_any(
        self,
        text: str,
        phrases: set[str],
    ) -> bool:

        return any(
            self._normalize(phrase) in text
            for phrase in phrases
        )

    def _normalize(
        self,
        value: str,
    ) -> str:

        normalized = unicodedata.normalize(
            "NFKD",
            value,
        )

        without_diacritics = "".join(
            character
            for character in normalized
            if not unicodedata.combining(
                character
            )
        )

        return " ".join(
            without_diacritics
            .lower()
            .replace("_", " ")
            .replace("-", " ")
            .split()
        )