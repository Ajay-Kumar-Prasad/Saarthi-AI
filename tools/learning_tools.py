"""
Saarthi AI — MCP Tool wrappers for the Learning Agent.

Two MCP servers are used:
  1. Notes MCP   — stores book notes, course summaries, study logs
  2. Calendar MCP — schedules and reads study session blocks

In the hackathon, these call real MCP endpoints configured via
environment variables (MCP_NOTES_URL, MCP_CALENDAR_URL).
For local dev without MCP, the functions fall back to mock data
when MOCK_MCP=true is set in the environment.
"""

import os
import logging
import httpx
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MOCK_MCP = os.getenv("MOCK_MCP", "false").lower() == "true"
MCP_NOTES_URL = os.getenv("MCP_NOTES_URL", "http://localhost:3001")
MCP_CALENDAR_URL = os.getenv("MCP_CALENDAR_URL", "http://localhost:3002")
MCP_TIMEOUT = 10  # seconds


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _post(base_url: str, path: str, payload: dict) -> dict:
    """POST to an MCP server endpoint and return JSON response."""
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        resp = await client.post(f"{base_url}{path}", json=payload)
        resp.raise_for_status()
        body = resp.json()
        if not isinstance(body, dict):
            raise ValueError(f"Invalid MCP response from {path}: expected object")
        return body


# ── Notes MCP ─────────────────────────────────────────────────────────────────

async def save_learning_note(
    user_id: str,
    resource_title: str,
    note_content: str,
    tags: list[str] | None = None,
) -> dict:
    """
    Save a study note to the Notes MCP server.
    Called when the user logs what they learned from a book/course.

    Returns:
        { "note_id": str, "saved": bool }
    """
    if MOCK_MCP:
        logger.info("[MOCK] Saving note for resource: %s", resource_title)
        return {
            "note_id": "mock-note-001",
            "saved": True,
            "resource": resource_title,
        }

    return await _post(
        MCP_NOTES_URL,
        "/notes/create",
        {
            "user_id": user_id,
            "title": f"Study note — {resource_title}",
            "content": note_content,
            "tags": tags or ["learning", resource_title.lower().replace(" ", "-")],
        },
    )


async def get_learning_notes(user_id: str, resource_title: str | None = None) -> list[dict]:
    """
    Retrieve notes from the Notes MCP server, optionally filtered
    to a specific book or course.

    Returns:
        List of note objects: [{ "note_id", "title", "content", "tags", "created_at" }]
    """
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

    params: dict = {"user_id": user_id, "tag": "learning"}
    if resource_title:
        params["search"] = resource_title

    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        resp = await client.get(f"{MCP_NOTES_URL}/notes", params=params)
        resp.raise_for_status()
        return resp.json().get("notes", [])


# ── Calendar MCP ──────────────────────────────────────────────────────────────

async def create_study_calendar_event(
    user_id: str,
    title: str,
    start_time: datetime,
    duration_minutes: int = 60,
    description: str = "",
) -> dict:
    """
    Create a study session block on Google Calendar via MCP.

    Returns:
        { "event_id": str, "html_link": str, "start": str, "end": str }
    """
    if MOCK_MCP:
        logger.info("[MOCK] Creating calendar event: %s at %s", title, start_time)
        return {
            "event_id": "mock-cal-event-001",
            "html_link": "https://calendar.google.com/mock",
            "start": start_time.isoformat(),
            "end": (start_time + timedelta(minutes=duration_minutes)).isoformat(),
        }

    return await _post(
        MCP_CALENDAR_URL,
        "/events/create",
        {
            "user_id": user_id,
            "summary": f"📚 {title}",
            "description": description or f"Saarthi study block — {title}",
            "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Kolkata"},
            "end": {
                "dateTime": (start_time + timedelta(minutes=duration_minutes)).isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "colorId": "7",  # Teal — matches the Learning Agent color in the dashboard
        },
    )


async def get_calendar_events(
    user_id: str,
    date: str,                      # ISO date string e.g. "2026-04-05"
) -> list[dict]:
    """
    Fetch all calendar events on a given date so we can detect
    scheduling conflicts before creating a study block.

    Returns:
        List of events: [{ "event_id", "summary", "start", "end" }]
    """
    if MOCK_MCP:
        logger.info("[MOCK] Fetching calendar events for %s", date)
        # Simulate a busy morning
        return [
            {
                "event_id": "mock-evt-001",
                "summary": "Team standup",
                "start": f"{date}T08:30:00+05:30",
                "end": f"{date}T09:00:00+05:30",
            },
            {
                "event_id": "mock-evt-002",
                "summary": "Work deep-focus block",
                "start": f"{date}T10:00:00+05:30",
                "end": f"{date}T12:00:00+05:30",
            },
        ]

    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        resp = await client.get(
            f"{MCP_CALENDAR_URL}/events",
            params={"user_id": user_id, "date": date},
        )
        resp.raise_for_status()
        body = resp.json()
        if not isinstance(body, dict):
            return []
        events = body.get("events", [])
        return events if isinstance(events, list) else []


async def delete_calendar_event(user_id: str, event_id: str) -> dict:
    """
    Delete a calendar event by ID. Used for rollback when DB save fails.
    """
    if MOCK_MCP:
        logger.info("[MOCK] Deleting calendar event: %s", event_id)
        return {"deleted": True, "event_id": event_id}

    if not event_id:
        return {"deleted": False, "error": "event_id is required"}

    return await _post(
        MCP_CALENDAR_URL,
        "/events/delete",
        {"user_id": user_id, "event_id": event_id},
    )


async def find_free_slot(
    user_id: str,
    date: str,
    duration_minutes: int = 60,
    prefer_morning: bool = False,
) -> dict | None:
    """
    Given a date, find the first free slot of the requested duration.
    Checks the Calendar MCP and avoids conflicts with existing events.

    Returns:
        { "start": datetime, "end": datetime } or None if no slot found.
    """
    events = await get_calendar_events(user_id, date)

    # Build busy intervals as (start_hour_float, end_hour_float)
    busy: list[tuple[float, float]] = []
    for evt in events:
        try:
            s = datetime.fromisoformat(evt["start"])
            e = datetime.fromisoformat(evt["end"])
            busy.append((s.hour + s.minute / 60, e.hour + e.minute / 60))
        except Exception:
            continue

    busy.sort()

    # Working window: 6am - 10pm (or 6am - noon for morning preference).
    window_start = 6.0
    window_end = 12.0 if prefer_morning else 22.0
    slot_hours = duration_minutes / 60

    candidate = window_start
    for b_start, b_end in busy:
        if candidate + slot_hours <= b_start:
            break           # free slot found before this busy block
        candidate = max(candidate, b_end)

    if candidate + slot_hours > window_end:
        return None         # no slot found today

    start_dt = datetime.fromisoformat(f"{date}T{int(candidate):02d}:{int((candidate % 1) * 60):02d}:00+05:30")
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return {"start": start_dt, "end": end_dt}
