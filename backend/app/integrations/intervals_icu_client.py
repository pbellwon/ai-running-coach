from __future__ import annotations

import os
from datetime import date, datetime

import requests


class IntervalsIcuClient:
    BASE_URL = "https://intervals.icu/api/v1"

    def __init__(
        self,
        api_key: str | None = None,
        athlete_id: str | None = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("INTERVALS_API_KEY")
        )

        self.athlete_id = (
            athlete_id
            or os.getenv(
                "INTERVALS_ATHLETE_ID",
                "0",
            )
        )

        if not self.api_key:
            raise ValueError(
                "INTERVALS_API_KEY is not configured."
            )

    def get_athlete(self) -> dict:
        return self._get_json(
            f"/athlete/{self.athlete_id}"
        )

    def get_activities(
        self,
        oldest: date | datetime | str,
        newest: date | datetime | str,
    ) -> list[dict]:
        oldest_value, newest_value = (
            self._normalize_range(
                oldest,
                newest,
            )
        )

        data = self._get_json(
            f"/athlete/{self.athlete_id}/activities",
            params={
                "oldest": oldest_value.isoformat(),
                "newest": newest_value.isoformat(),
            },
        )

        if not isinstance(data, list):
            raise RuntimeError(
                "Intervals.icu activities response "
                "is not a list."
            )

        return data

    def get_wellness(
        self,
        oldest: date | datetime | str,
        newest: date | datetime | str,
    ) -> list[dict]:
        oldest_value, newest_value = (
            self._normalize_range(
                oldest,
                newest,
            )
        )

        data = self._get_json(
            f"/athlete/{self.athlete_id}/wellness",
            params={
                "oldest": oldest_value.isoformat(),
                "newest": newest_value.isoformat(),
            },
        )

        if not isinstance(data, list):
            raise RuntimeError(
                "Intervals.icu wellness response "
                "is not a list."
            )

        return data

    def _get_json(
        self,
        path: str,
        params: dict | None = None,
    ):
        url = f"{self.BASE_URL}{path}"

        response = requests.get(
            url,
            params=params,
            auth=(
                "API_KEY",
                self.api_key,
            ),
            timeout=30,
        )

        self._raise_for_status(response)

        return response.json()

    def _normalize_range(
        self,
        oldest: date | datetime | str,
        newest: date | datetime | str,
    ) -> tuple[date, date]:
        oldest_value = self._normalize_date(
            oldest
        )

        newest_value = self._normalize_date(
            newest
        )

        if oldest_value > newest_value:
            raise ValueError(
                "oldest cannot be later than newest."
            )

        return oldest_value, newest_value

    def _normalize_date(
        self,
        value: date | datetime | str,
    ) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            normalized = value.strip()

            try:
                return date.fromisoformat(
                    normalized
                )
            except ValueError as exc:
                raise ValueError(
                    "Date must use YYYY-MM-DD format."
                ) from exc

        raise TypeError(
            "Date must be date, datetime or ISO string."
        )

    def _raise_for_status(
        self,
        response: requests.Response,
    ) -> None:
        if response.ok:
            return

        if response.status_code == 401:
            raise RuntimeError(
                "Intervals.icu authentication failed "
                "(401 Unauthorized). Check API key."
            )

        if response.status_code == 403:
            raise RuntimeError(
                "Intervals.icu access denied "
                "(403 Forbidden)."
            )

        if response.status_code == 429:
            retry_after = response.headers.get(
                "Retry-After"
            )

            raise RuntimeError(
                "Intervals.icu rate limit exceeded. "
                f"Retry-After: {retry_after}"
            )

        raise RuntimeError(
            "Intervals.icu request failed: "
            f"{response.status_code} "
            f"{response.text[:500]}"
        )