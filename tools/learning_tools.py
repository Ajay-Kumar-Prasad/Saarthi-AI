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
    resource_id: str | None = None,
) -> dict:
    if not user_id:
        return {"note_id": None, "saved": False, "error": "user_id is required"}
    if MOCK_MCP:
        logger.info("[MOCK] Saving note user_id=%s resource=%s", user_id, resource_title)
        return {"note_id": "mock-note-001", "saved": True, "resource": resource_title}
    from tools.notes_mcp import save_learning_note as _save
    return await _save(user_id, resource_title, note_content, tags, resource_id=resource_id)


async def get_learning_notes(user_id: str, resource_title: str | None = None) -> list[dict]:
    if not user_id:
        logger.warning("Notes read rejected user_id=<missing>")
        return []
    if MOCK_MCP:
        logger.info("[MOCK] Fetching learning notes user_id=%s", user_id)
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

    token_path = os.getenv("GOOGLE_TOKEN_PATH", "").strip()
    if not token_path:
        raise RuntimeError("GOOGLE_TOKEN_PATH is required for real calendar access.")
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


def _resolve_calendar_scope(user_id: str) -> tuple[str, bool]:
    """
    Resolve calendar ID with optional per-user mapping.
    Returns (calendar_id, is_dedicated_to_user).
    """
    import json

    raw_map = os.getenv("SAARTHI_USER_CALENDAR_MAP", "").strip()
    if raw_map:
        try:
            parsed = json.loads(raw_map)
            if isinstance(parsed, dict):
                cid = parsed.get(user_id)
                if isinstance(cid, str) and cid.strip():
                    return cid.strip(), True
        except Exception as exc:
            logger.warning("Invalid SAARTHI_USER_CALENDAR_MAP; falling back to shared calendar: %s", exc)

    calendar_id = os.getenv("SAARTHI_CALENDAR_ID", "").strip()
    if not calendar_id:
        raise RuntimeError("SAARTHI_CALENDAR_ID is required when user map is not configured.")
    return calendar_id, False


async def create_study_calendar_event(
    user_id: str,
    title: str,
    start_time: datetime,
    duration_minutes: int = 60,
    description: str = "",
) -> dict:
    if not user_id:
        return {"event_id": None, "error": "user_id is required"}
    if MOCK_MCP:
        logger.info("[MOCK] Creating calendar event user_id=%s title=%s at=%s", user_id, title, start_time)
        return {
            "event_id": "mock-cal-event-001",
            "html_link": "https://calendar.google.com/mock",
            "start": start_time.isoformat(),
            "end": (start_time + timedelta(minutes=duration_minutes)).isoformat(),
        }

    try:
        calendar_id, dedicated = _resolve_calendar_scope(user_id)
        service = _get_calendar_service()
        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            "summary": f"📚 {title}",
            "description": description or f"Saarthi AI study block — {title}",
            "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Kolkata"},
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
        created = service.events().insert(calendarId=calendar_id, body=event).execute()
        logger.info(
            "Calendar write success user_id=%s event_id=%s calendar_id=%s dedicated=%s access=create",
            user_id, created.get("id"), calendar_id, dedicated,
        )
        return {
            "event_id": created["id"],
            "html_link": created.get("htmlLink", ""),
            "start": created["start"]["dateTime"],
            "end": created["end"]["dateTime"],
        }
    except Exception as exc:
        logger.error("Calendar write failure user_id=%s access=create error=%s", user_id, exc)
        return {"event_id": None, "error": str(exc)}


async def get_calendar_events(user_id: str, date: str) -> list[dict]:
    if not user_id:
        logger.warning("Calendar read rejected user_id=<missing>")
        return []
    if MOCK_MCP:
        logger.info("[MOCK] Fetching calendar events user_id=%s date=%s", user_id, date)
        return [
            {"event_id": "mock-evt-001", "summary": "Team standup",
             "start": f"{date}T08:30:00+05:30", "end": f"{date}T09:00:00+05:30"},
            {"event_id": "mock-evt-002", "summary": "Work deep-focus block",
             "start": f"{date}T10:00:00+05:30", "end": f"{date}T12:00:00+05:30"},
        ]

    try:
        calendar_id, dedicated = _resolve_calendar_scope(user_id)
        service = _get_calendar_service()
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
                    "Calendar read rejected user_id=%s event_id=%s reason=owner_mismatch owner=%s",
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
    if not user_id:
        return {"deleted": False, "error": "user_id is required"}
    if MOCK_MCP:
        logger.info("[MOCK] Deleting calendar event user_id=%s event_id=%s", user_id, event_id)
        return {"deleted": True, "event_id": event_id}

    if not event_id:
        return {"deleted": False, "error": "event_id is required"}

    try:
        calendar_id, dedicated = _resolve_calendar_scope(user_id)
        service = _get_calendar_service()
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        private_meta = (event.get("extendedProperties", {}) or {}).get("private", {}) or {}
        owner = private_meta.get("user_id")
        if not dedicated and owner != user_id:
            logger.warning(
                "Calendar delete rejected user_id=%s event_id=%s owner=%s",
                user_id, event_id, owner,
            )
            return {"deleted": False, "error": "event does not belong to user"}

        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info(
            "Calendar delete success user_id=%s event_id=%s calendar_id=%s dedicated=%s",
            user_id, event_id, calendar_id, dedicated,
        )
        return {"deleted": True, "event_id": event_id}
    except Exception as exc:
        logger.error("Calendar delete failure user_id=%s event_id=%s error=%s", user_id, event_id, exc)
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
