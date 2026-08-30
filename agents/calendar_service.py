"""Google Calendar adapter used by travel/business agents.

This adapter performs real Calendar API calls once the user's Google OAuth
credentials are configured. It never performs purchases or financial actions.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarService:
    def __init__(self, credentials_file: str | None = None, token_file: str | None = None) -> None:
        self.credentials_file = credentials_file or os.environ.get(
            "GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json"
        )
        self.token_file = token_file or os.environ.get(
            "GOOGLE_CALENDAR_TOKEN_FILE", ".google_calendar_token.json"
        )
        self._service: Any | None = None

    def _build(self) -> Any:
        if self._service is not None:
            return self._service

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Google Calendar dependencies are not installed. Run pip install -r requirements.txt"
            ) from exc

        creds = None
        token_path = Path(self.token_file)
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif not creds or not creds.valid:
            credentials_path = Path(self.credentials_file)
            if not credentials_path.exists():
                raise RuntimeError(
                    "Google Calendar OAuth is not configured yet. "
                    f"Missing OAuth client file: {credentials_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def list_upcoming(self, time_min: str, max_results: int = 20, calendar_id: str = "primary") -> list[dict[str, Any]]:
        service = self._build()
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return result.get("items", [])

    def create_event(
        self,
        *,
        title: str,
        start: str,
        end: str,
        timezone: str,
        description: str = "",
        location: str = "",
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        service = self._build()
        body = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
        }
        return service.events().insert(calendarId=calendar_id, body=body).execute()

    def update_event(self, event_id: str, changes: dict[str, Any], calendar_id: str = "primary") -> dict[str, Any]:
        service = self._build()
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        event.update(changes)
        return service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        service = self._build()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
