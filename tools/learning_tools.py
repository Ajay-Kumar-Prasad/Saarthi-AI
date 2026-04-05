"""
Saarthi AI — MCP Tool wrappers for the Learning Agent.

Two MCP servers are used:
  1. Notes MCP   — stores book notes, course summaries, study logs
  2. Calendar MCP — schedules and reads study session blocks

Real implementations use Google Calendar API (token.json) and AlloyDB (life_logs).
Falls back to mock data when MOCK_MCP=true.
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MOCK_MCP = os.getenv("MOCK_MCP", "false").lower() == "true"
MCP_TIMEOUT = 10


# ── Notes MCP ─────────────────────────────────────────────────────────────────

async def save_learning_note(
    user_id: str,
    resource_title: str,
    note_content: str,
    tags: list[str] | None = None,
) -> dict:
    if MOCK_MCP:
        logger.info("[MOCK] Saving note for resource: %s", resource_title)
        return {"note_id": "mock-note-001", "saved": True, "resource": resource_title}
    from tools.notes_mcp import save_learning_note as _save
    return await _save(user_id, resource_title, note_content, tags)


async def get_learning_notes(user_id: str, resource_title: str | None = None) -> list[dict]:
    if MOCK_MCP:
        logger.info("[MOCK] Fetching learning notes")
        return [
            {
                "note_id": "mock-note-001",
                "title": "Study note — Python Crash Course",
                "content": "Chapter 9 — classes and objects. Key: __init__ is the constructor.",
                "tags": ["learning", "python"],
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
    from tools.notes_mcp import get_learning_notes as _get
    return await _get(user_id, resource_title)


# ── Calendar MCP ──────────────────────────────────────────────────────────────

def _get_calendar_service():
    """Load OAuth credentials and return Google Calendar API service."""
    import json
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_path = os.getenv("GOOGLE_TOKEN_PATH", "/home/ajayk10440/Saarthi-AI/token.json")
    with open(token_path) as f:
        data = json.load(f)

    creds = Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        data["token"] = creds.token
        with open(token_path, "w") as f:
            json.dump(data, f, indent=2)

    return build("calendar", "v3", credentials=creds)


async def create_study_calendar_event(
    user_id: str,
    title: str,
    start_time: datetime,
    duration_minutes: int = 60,
    description: str = "",
) -> dict:
    if MOCK_MCP:
        logger.info("[MOCK] Creating calendar event: %s at %s", title, start_time)
        return {
            "event_id": "mock-cal-event-001",
            "html_link": "https://calendar.google.com/mock",
            "start": start_time.isoformat(),
            "end": (start_time + timedelta(minutes=duration_minutes)).isoformat(),
        }

    try:
        calendar_id = os.getenv("SAARTHI_CALENDAR_ID", "ajayk10440@gmail.com")
        service = _get_calendar_service()
        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            "summary": f"📚 {title}",
            "description": description or f"Saarthi AI study block — {title}",
            "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Kolkata"},
            "colorId": "7",
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
        }
        created = service.events().insert(calendarId=calendar_id, body=event).execute()
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
    if MOCK_MCP:
        logger.info("[MOCK] Fetching calendar events for %s", date)
        return [
            {"event_id": "mock-evt-001", "summary": "Team standup",
             "start": f"{date}T08:30:00+05:30", "end": f"{date}T09:00:00+05:30"},
            {"event_id": "mock-evt-002", "summary": "Work deep-focus block",
             "start": f"{date}T10:00:00+05:30", "end": f"{date}T12:00:00+05:30"},
        ]

    try:
        calendar_id = os.getenv("SAARTHI_CALENDAR_ID", "ajayk10440@gmail.com")
        service = _get_calendar_service()
        day_start = f"{date}T00:00:00+05:30"
        day_end = f"{date}T23:59:59+05:30"

        result = service.events().list(
            calendarId=calendar_id,
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
    if MOCK_MCP:
        logger.info("[MOCK] Deleting calendar event: %s", event_id)
        return {"deleted": True, "event_id": event_id}

    if not event_id:
        return {"deleted": False, "error": "event_id is required"}

    try:
        calendar_id = os.getenv("SAARTHI_CALENDAR_ID", "ajayk10440@gmail.com")
        service = _get_calendar_service()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return {"deleted": True, "event_id": event_id}
    except Exception as exc:
        logger.error("Failed to delete calendar event: %s", exc)
        return {"deleted": False, "error": str(exc)}


async def find_free_slot(
    user_id: str,
    date: str,
    duration_minutes: int = 60,
    prefer_morning: bool = False,
) -> dict | None:
    events = await get_calendar_events(user_id, date)

    busy: list[tuple[float, float]] = []
    for evt in events:
        try:
            s = datetime.fromisoformat(evt["start"])
            e = datetime.fromisoformat(evt["end"])
            busy.append((s.hour + s.minute / 60, e.hour + e.minute / 60))
        except Exception:
            continue

    busy.sort()

    window_start = 6.0
    window_end = 12.0 if prefer_morning else 22.0
    slot_hours = duration_minutes / 60

    candidate = window_start
    for b_start, b_end in busy:
        if candidate + slot_hours <= b_start:
            break
        candidate = max(candidate, b_end)

    if candidate + slot_hours > window_end:
        return None

    start_dt = datetime.fromisoformat(
        f"{date}T{int(candidate):02d}:{int((candidate % 1) * 60):02d}:00+05:30"
    )
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return {"start": start_dt, "end": end_dt}
