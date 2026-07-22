import os

import gspread


class GoogleSheetsPlanSource:

    def __init__(
        self,
        spreadsheet_id: str | None = None,
        worksheet_name: str | None = None,
        credentials_path: str | None = None,
    ):

        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_PLAN_SPREADSHEET_ID")
        self.worksheet_name = worksheet_name or os.getenv(
            "GOOGLE_PLAN_WORKSHEET_NAME",
            "plan_import",
        )
        self.credentials_path = credentials_path or os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            "credentials/google_service_account.json",
        )

        if not self.spreadsheet_id:
            raise ValueError("Missing GOOGLE_PLAN_SPREADSHEET_ID")

        if not self.worksheet_name:
            raise ValueError("Missing GOOGLE_PLAN_WORKSHEET_NAME")

        if not self.credentials_path:
            raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_FILE")

    def fetch_rows(self) -> list[dict]:

        client = gspread.service_account(filename=self.credentials_path)

        spreadsheet = client.open_by_key(self.spreadsheet_id)

        worksheet = spreadsheet.worksheet(self.worksheet_name)

        rows = worksheet.get_all_records()

        return [self._normalize_row(row) for row in rows if not self._is_empty_row(row)]

    def _normalize_row(self, row: dict) -> dict:

        return {
            str(key).strip(): self._clean_value(value)
            for key, value in row.items()
        }

    def _clean_value(self, value) -> str:

        if value is None:
            return ""

        return str(value).strip()

    def _is_empty_row(self, row: dict) -> bool:

        return all(str(value).strip() == "" for value in row.values())