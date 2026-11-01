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
    def _correction_worksheet(self):
        client = gspread.service_account(filename=self.credentials_path)
        return client.open_by_key(self.spreadsheet_id).worksheet(self.worksheet_name)

    def correction_snapshot(self):
        # Preserve exact text, physical row positions, empty cells and additional columns.
        worksheet = self._correction_worksheet()
        values = worksheet.get_all_values()
        if not values or len(set(values[0])) != len(values[0]):
            raise ValueError('Missing or duplicate plan headers')
        headers = values[0]
        if any(len(row) > len(headers) for row in values[1:]):
            raise ValueError('Plan contains cells without headers')
        return {'source': [self.spreadsheet_id, str(worksheet.id)], 'headers': headers,
                'rows': [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in values[1:]]}

    def write_correction(self, snapshot, row_number, before, after):
        from gspread.utils import rowcol_to_a1
        worksheet = self._correction_worksheet()
        if [self.spreadsheet_id, str(worksheet.id)] != snapshot['source']:
            raise ValueError('Worksheet changed')
        changes = [{'range': rowcol_to_a1(row_number, i + 1), 'values': [[after[key]]]}
                   for i, key in enumerate(snapshot['headers']) if before[key] != after[key]]
        # RAW prevents user text beginning with '=' from becoming a spreadsheet formula.
        worksheet.batch_update(changes, value_input_option='RAW')

    def race_calendar_snapshot(self):
        client = gspread.service_account(filename=self.credentials_path)
        spreadsheet = client.open_by_key(self.spreadsheet_id)
        worksheet = spreadsheet.worksheet(os.getenv('GOOGLE_RACE_WORKSHEET_NAME', 'race_calendar'))
        values = worksheet.get_all_values()
        if not values or len(set(values[0])) != len(values[0]) or any(not h.strip() for h in values[0]):
            raise ValueError('Missing or duplicate calendar headers')
        headers = values[0]
        if any(len(row) > len(headers) for row in values[1:]):
            raise ValueError('Calendar contains cells without headers')
        return {'source': [self.spreadsheet_id, str(worksheet.id)], 'headers': headers,
                'rows': [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in values[1:]]}

    def write_generated_plan(self, before, after):
        """One atomic Sheets request including grid growth; only changed cells are touched."""
        worksheet = self._correction_worksheet()
        if [self.spreadsheet_id, str(worksheet.id)] != before['source']:
            raise ValueError('Worksheet changed')
        if before['headers'] != after['headers'] or len(after['rows']) < len(before['rows']):
            raise ValueError('Plan headers or existing rows cannot be removed')
        requests = []
        needed_rows = len(after['rows']) + 1
        if needed_rows > worksheet.row_count:
            requests.append({'appendDimension': {'sheetId': worksheet.id, 'dimension': 'ROWS',
                                                 'length': needed_rows - worksheet.row_count}})
        for row_index, row in enumerate(after['rows'], 1):
            old = before['rows'][row_index - 1] if row_index <= len(before['rows']) else {}
            for column_index, header in enumerate(after['headers']):
                value = row[header]
                if value == old.get(header, ''):
                    continue
                requests.append({'updateCells': {
                    'range': {'sheetId': worksheet.id, 'startRowIndex': row_index, 'endRowIndex': row_index + 1,
                              'startColumnIndex': column_index, 'endColumnIndex': column_index + 1},
                    'rows': [{'values': [{'userEnteredValue': {'stringValue': value}}]}],
                    'fields': 'userEnteredValue'}})
        if requests:
            # stringValue preserves literal user text, including leading '='. No formula evaluation.
            worksheet.spreadsheet.batch_update({'requests': requests})
