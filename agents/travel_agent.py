"""Travel, hotel, restaurant, reservation, itinerary, and calendar specialist."""
from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .calendar_tool import GoogleCalendarTool

TRAVEL_SYSTEM_PROMPT = """You are the Travel & Reservations specialist in an autonomous agent team. Understand Arabic or English naturally. Handle trip planning, flights, hotels, restaurants, comparisons, itineraries, reservation preparation, and calendar-ready schedules. Prefer current verified availability and prices when connected travel/search tools are available. Never invent availability, prices, confirmation numbers, or bookings. Never purchase, book, cancel, or spend money without explicit user approval for that specific financial action. Google Calendar is available through an authorized local tool. Calendar reads are allowed when needed. Calendar writes must only occur when the user's request clearly asks to add/update/delete a calendar event; never claim a calendar action succeeded unless the tool confirms it. Keep dates, local time zones, party size, traveler count, budget, cancellation rules, and reservation constraints explicit. If another execution tool is unavailable, clearly state the missing capability instead of pretending the action happened."""


class TravelAgent(BaseAgent):
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        client: Any | None = None,
        calendar: GoogleCalendarTool | None = None,
        calendar_only: bool = False,
    ) -> None:
        self._calendar = calendar
        self._calendar_only = calendar_only
        if calendar_only:
            self.name = "travel_agent"
            self.system_prompt = TRAVEL_SYSTEM_PROMPT
            self.model = model
            self.client = client
        else:
            super().__init__(name="travel_agent", system_prompt=TRAVEL_SYSTEM_PROMPT, model=model, client=client)

    @property
    def calendar(self) -> GoogleCalendarTool:
        """Lazy-load Calendar so normal travel planning does not trigger OAuth."""
        if self._calendar is None:
            self._calendar = GoogleCalendarTool()
        return self._calendar

    def calendar_events(self, time_min: str, time_max: str, max_results: int = 50) -> list[dict[str, Any]]:
        """Read events in an explicit RFC3339 time window."""
        return self.calendar.list_events(time_min, time_max, max_results=max_results)

    def add_calendar_event(self, body: dict[str, Any]) -> dict[str, Any]:
        """Create an event after the caller has established explicit user intent."""
        return self.calendar.create_event(body)

    def update_calendar_event(self, event_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """Update an event after the caller has established explicit user intent."""
        return self.calendar.update_event(event_id, body)

    def delete_calendar_event(self, event_id: str) -> None:
        """Delete an event after the caller has established explicit user intent."""
        self.calendar.delete_event(event_id)
