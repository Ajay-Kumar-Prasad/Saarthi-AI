"""
Saarthi AI — Real Google Calendar MCP implementation.
Uses OAuth2 credentials from token.json.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "/home/ajayk10440/Saarthi-AI/token.json")
CALENDAR_ID = os.getenv("SAARTHI_CALENDAR_ID", "ajayk10440@gmail.com")
TIMEZONE = "Asia/Kolkata"


def _get_service():
    """Load credentials and return Calendar API service."""
    with open(TOKEN_PATH) as f:
        data = json.load(f)

    creds = Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        data["token"] = creds.token
        with open(TOKEN_PATH, "w") as f:
            json.dump(data, f, indent=2)

    return build("calendar", "v3", credentials=creds)


async def create_study_calendar_event(
    user_id: str,
    title: str,
    start_time: datetime,
    duration_minutes: int = 60,
    description: str = "",
) -> dict:
    """Create a real Google Calendar event for a study session."""
    try:
        service = _get_service()
        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            "summary": f"📚 {title}",
            "description": description or f"Saarthi AI study block — {title}",
            "start": {"dateTime": start_time.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end_time.isoformat(), "timeZone": TIMEZONE},
            "colorId": "7",
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
        }

        created = service.events().insert(
            calendarId=CALENDAR_ID, body=event
        ).execute()

        logger.info("Calendar event created: %s", created.get("id"))
        return {
            "event_id": created["id"],
            "html_link": created.get("htmlLink", ""),
            "start": created["start"]["dateTime"],
            "end": created["end"]["dateTime"],
        }
    except Exception as exc:
        logger.error("Failed to create calendar event: %s", exc)
        return {"event_id": None, "error": str(exc)}


async def get_calendar_events(user_id: str, date: str) -> list[dict]:
    """Fetch all events on a given date from Google Calendar."""
    try:
        service = _get_service()

        day_start = f"{date}T00:00:00+05:30"
        day_end = f"{date}T23:59:59+05:30"

        result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=day_start,
            timeMax=day_end,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for evt in result.get("items", []):
            start = evt.get("start", {})
            end = evt.get("end", {})
            events.append({
                "event_id": evt["id"],
                "summary": evt.get("summary", ""),
                "start": start.get("dateTime", start.get("date", "")),
                "end": end.get("dateTime", end.get("date", "")),
            })

        logger.info("Found %d events on %s", len(events), date)
        return events
    except Exception as exc:
        logger.error("Failed to fetch calendar events: %s", exc)
        return []


async def delete_calendar_event(user_id: str, event_id: str) -> dict:
    """Delete a Google Calendar event by ID."""
    try:
        service = _get_service()
        service.events().delete(
            calendarId=CALENDAR_ID, eventId=event_id
        ).execute()
        logger.info("Deleted calendar event: %s", event_id)
        return {"deleted": True, "event_id": event_id}
    except Exception as exc:
        logger.error("Failed to delete calendar event: %s", exc)
        return {"deleted": False, "error": str(exc)}
