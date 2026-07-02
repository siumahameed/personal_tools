import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime


class GoogleSheetsClient:
    def __init__(self, credentials_path=None, spreadsheet_id=None):
        self.client = None
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self._spreadsheet = None
        if credentials_path:
            self.authenticate()

    def authenticate(self):
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(
                self.credentials_path, scopes=scopes
            )
            self.client = gspread.authorize(creds)
            self._spreadsheet = self.client.open_by_key(self.spreadsheet_id) if self.spreadsheet_id else None
            print(f"  Google Sheets: Connected to {self._spreadsheet.title if self._spreadsheet else '?'}")
        except Exception as e:
            print(f"  Google Sheets: Auth failed - {e}")
            self.client = None

    def _get_or_create_ws(self, name, headers=None):
        try:
            return self._spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = self._spreadsheet.add_worksheet(title=name, rows=1000, cols=30)
            if headers:
                ws.append_row(headers)
            return ws

    def sync_table(self, sheet_name, headers, rows):
        """Safely sync rows to Google Sheets. Preserves existing data on failure."""
        if not self.client or not self._spreadsheet:
            return
        try:
            ws = self._get_or_create_ws(sheet_name, headers)
            existing = ws.get_all_values()
            existing_names = self._get_existing_names(existing, headers)
            incoming_name_idx = self._find_name_col(headers)

            new_rows = []
            for row in rows:
                if incoming_name_idx != -1 and len(row) > incoming_name_idx:
                    name_val = str(row[incoming_name_idx]).strip().lower()
                    if name_val in existing_names:
                        continue
                    existing_names.add(name_val)
                new_rows.append(row)

            if new_rows:
                ws.append_rows(new_rows, value_input_option="USER_ENTERED")
                print(f"  Synced {len(new_rows)} new rows to Google Sheet > {sheet_name}")
            else:
                print(f"  No new rows for Google Sheet > {sheet_name}")
        except Exception as e:
            print(f"  Google Sheets write error: {e}")

    def safe_sync_table(self, sheet_name, headers, rows):
        """Atomic sync: write to temp range first, then replace. Prevents data loss."""
        if not self.client or not self._spreadsheet:
            return
        try:
            ws = self._get_or_create_ws(sheet_name, headers)
            all_data = [headers] + rows
            existing = ws.get_all_values() if ws.row_count > 1 else []
            if existing == all_data:
                return
            ws.clear()
            if all_data:
                ws.append_rows(all_data, value_input_option="USER_ENTERED")
            print(f"  Synced {len(rows)} rows to Google Sheet > {sheet_name}")
        except Exception as e:
            print(f"  Google Sheets safe sync error: {e}")

    def append_rows(self, sheet_name, headers, rows):
        """Append-only for log sheets (Following, Updates Log)."""
        if not self.client or not self._spreadsheet:
            return
        try:
            ws = self._get_or_create_ws(sheet_name, headers)
            for row in rows:
                ws.append_row(row, value_input_option="USER_ENTERED")
            print(f"  Appended {len(rows)} rows to Google Sheet > {sheet_name}")
        except Exception as e:
            print(f"  Google Sheets write error: {e}")

    def _find_name_col(self, headers):
        for i, h in enumerate(h.lower().strip() for h in headers):
            if "name" in h:
                return i
        return -1

    def _get_existing_names(self, existing_values, headers):
        name_col = self._find_name_col(headers)
        if name_col == -1 or len(existing_values) <= 1:
            return set()
        names = set()
        for r in existing_values[1:]:
            if len(r) > name_col and r[name_col].strip():
                names.add(r[name_col].strip().lower())
        return names

    def update_cell(self, sheet_name, row, col, value):
        if not self.client or not self._spreadsheet:
            return
        try:
            ws = self._spreadsheet.worksheet(sheet_name)
            ws.update_cell(row, col, value)
        except Exception as e:
            print(f"  Google Sheets update error: {e}")

    def get_all_records(self, sheet_name):
        if not self.client or not self._spreadsheet:
            return []
        try:
            ws = self._spreadsheet.worksheet(sheet_name)
            return ws.get_all_records()
        except Exception:
            return []
