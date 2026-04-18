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

TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "").strip()
CALENDAR_ID = os.getenv("SAARTHI_CALENDAR_ID", "").strip()
TIMEZONE = "Asia/Kolkata"


def _get_service():
    """Load credentials and return Calendar API service."""
    if not TOKEN_PATH:
        raise RuntimeError("GOOGLE_TOKEN_PATH is required for calendar integration.")
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


def _resolve_calendar_scope(user_id: str) -> tuple[str, bool]:
    raw_map = os.getenv("SAARTHI_USER_CALENDAR_MAP", "").strip()
    if raw_map:
        try:
            parsed = json.loads(raw_map)
            if isinstance(parsed, dict):
                cid = parsed.get(user_id)
                if isinstance(cid, str) and cid.strip():
                    return cid.strip(), True
        except Exception as exc:
            logger.warning("Invalid SAARTHI_USER_CALENDAR_MAP; using fallback calendar: %s", exc)
    if not CALENDAR_ID:
        raise RuntimeError("SAARTHI_CALENDAR_ID is required when no per-user calendar mapping is set.")
    return CALENDAR_ID, False


async def create_study_calendar_event(
    user_id: str,
    title: str,
    start_time: datetime,
    duration_minutes: int = 60,
    description: str = "",
) -> dict:
    """Create a real Google Calendar event for a study session."""
    if not user_id:
        return {"event_id": None, "error": "user_id is required"}
    try:
        service = _get_service()
        calendar_id, dedicated = _resolve_calendar_scope(user_id)
        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            "summary": f"📚 {title}",
            "description": description or f"Saarthi AI study block — {title}",
            "start": {"dateTime": start_time.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end_time.isoformat(), "timeZone": TIMEZONE},
            "extendedProperties": {
                "private": {
                    "user_id": user_id,
                    "agent": "learning",
                }
            },
            "colorId": "7",
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
        }

        created = service.events().insert(
            calendarId=calendar_id, body=event
        ).execute()

        logger.info(
            "Calendar create success user_id=%s event_id=%s calendar_id=%s dedicated=%s",
            user_id, created.get("id"), calendar_id, dedicated,
        )
        return {
            "event_id": created["id"],
            "html_link": created.get("htmlLink", ""),
            "start": created["start"]["dateTime"],
            "end": created["end"]["dateTime"],
        }
    except Exception as exc:
        logger.error("Calendar create failure user_id=%s error=%s", user_id, exc)
        return {"event_id": None, "error": str(exc)}


async def get_calendar_events(user_id: str, date: str) -> list[dict]:
    """Fetch all events on a given date from Google Calendar."""
    if not user_id:
        logger.warning("Calendar read rejected user_id=<missing>")
        return []
    try:
        service = _get_service()
        calendar_id, dedicated = _resolve_calendar_scope(user_id)

        day_start = f"{date}T00:00:00+05:30"
        day_end = f"{date}T23:59:59+05:30"

        result = service.events().list(
            calendarId=calendar_id,
            timeMin=day_start,
            timeMax=day_end,
            singleEvents=True,
            orderBy="startTime",
            privateExtendedProperty=f"user_id={user_id}",
        ).execute()

        events = []
        for evt in result.get("items", []):
            private_meta = (evt.get("extendedProperties", {}) or {}).get("private", {}) or {}
            owner = private_meta.get("user_id")
            if not dedicated and owner != user_id:
                logger.warning(
                    "Calendar read rejected user_id=%s event_id=%s owner=%s",
                    user_id, evt.get("id"), owner,
                )
                continue
            start = evt.get("start", {})
            end = evt.get("end", {})
            events.append({
                "event_id": evt["id"],
                "summary": evt.get("summary", ""),
                "start": start.get("dateTime", start.get("date", "")),
                "end": end.get("dateTime", end.get("date", "")),
            })

        logger.info(
            "Calendar read success user_id=%s date=%s count=%d calendar_id=%s dedicated=%s",
            user_id, date, len(events), calendar_id, dedicated,
        )
        return events
    except Exception as exc:
        logger.error("Calendar read failure user_id=%s date=%s error=%s", user_id, date, exc)
        return []


async def delete_calendar_event(user_id: str, event_id: str) -> dict:
    """Delete a Google Calendar event by ID."""
    if not user_id:
        return {"deleted": False, "error": "user_id is required"}
    if not event_id:
        return {"deleted": False, "error": "event_id is required"}
    try:
        service = _get_service()
        calendar_id, dedicated = _resolve_calendar_scope(user_id)
        event = service.events().get(
            calendarId=calendar_id, eventId=event_id
        ).execute()
        private_meta = (event.get("extendedProperties", {}) or {}).get("private", {}) or {}
        owner = private_meta.get("user_id")
        if not dedicated and owner != user_id:
            logger.warning("Calendar delete rejected user_id=%s event_id=%s owner=%s", user_id, event_id, owner)
            return {"deleted": False, "error": "event does not belong to user"}

        service.events().delete(
            calendarId=calendar_id, eventId=event_id
        ).execute()
        logger.info(
            "Calendar delete success user_id=%s event_id=%s calendar_id=%s dedicated=%s",
            user_id, event_id, calendar_id, dedicated,
        )
        return {"deleted": True, "event_id": event_id}
    except Exception as exc:
        logger.error("Calendar delete failure user_id=%s event_id=%s error=%s", user_id, event_id, exc)
        return {"deleted": False, "error": str(exc)}
