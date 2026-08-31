"""Google Calendar OAuth adapter for the agent team."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

class GoogleCalendarTool:
    def __init__(self, credentials_file: str | None = None, token_file: str | None = None, calendar_id: str | None = None) -> None:
        self.credentials_file = Path(credentials_file or os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "google_calendar_credentials.json"))
        self.token_file = Path(token_file or os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "google_calendar_token.json"))
        self.calendar_id = calendar_id or os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self._service: Any | None = None

    def authenticate(self) -> Any:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError("Google Calendar dependencies are not installed. Run pip install -r requirements.txt") from exc
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    raise FileNotFoundError(f"OAuth credentials file not found: {self.credentials_file}")
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
                creds = flow.run_local_server(port=0, open_browser=True)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._service

    @property
    def service(self) -> Any:
        return self._service or self.authenticate()

    def list_events(self, time_min: str, time_max: str, max_results: int = 50) -> list[dict[str, Any]]:
        result = self.service.events().list(calendarId=self.calendar_id, timeMin=time_min, timeMax=time_max, singleEvents=True, orderBy="startTime", maxResults=max_results).execute()
        return result.get("items", [])

    def create_event(self, body: dict[str, Any]) -> dict[str, Any]:
        return self.service.events().insert(calendarId=self.calendar_id, body=body).execute()

    def update_event(self, event_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.service.events().patch(calendarId=self.calendar_id, eventId=event_id, body=body).execute()

    def delete_event(self, event_id: str) -> None:
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
