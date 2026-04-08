"""
Saarthi AI — Workspace MCP client wrapper.

Wraps the local workspace-mcp Docker server so work_agent.py
can call Calendar, Gmail, Drive, Tasks, Docs tools via MCP.

Requires the Docker container running:
    docker run --rm --name workspace-mcp --env-file .env \
        -p 8080:8000 -v workspace_mcp_creds:/root/.google_workspace_mcp \
        local-workspace-mcp

Set MOCK_WORKSPACE_MCP=true in .env to skip Docker during testing.
"""

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

MOCK_WORKSPACE_MCP = os.getenv("MOCK_WORKSPACE_MCP", "false").lower() == "true"
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")


def _get_mcp_toolset():
    """Return a configured McpToolset pointed at the local workspace-mcp server."""
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StreamableHTTPConnectionParams,
    )
    token = os.getenv("MCP_AUTH_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=MCP_SERVER_URL,
            headers=headers,
        )
    )


# ── Mock helpers (used when MOCK_WORKSPACE_MCP=true) ─────────────────────────

async def mock_get_calendar_events(user_id: str, max_results: int = 10) -> list[dict]:
    return [
        {
            "id": "mock-evt-001",
            "summary": "Team standup",
            "start": "2026-04-10T09:00:00+05:30",
            "end":   "2026-04-10T09:30:00+05:30",
            "status": "confirmed",
        },
        {
            "id": "mock-evt-002",
            "summary": "Sprint planning",
            "start": "2026-04-10T14:00:00+05:30",
            "end":   "2026-04-10T15:30:00+05:30",
            "status": "confirmed",
        },
    ]


async def mock_create_calendar_event(
    summary: str, start: str, end: str, description: str = ""
) -> dict:
    return {
        "id": "mock-created-evt-001",
        "summary": summary,
        "start": start,
        "end": end,
        "htmlLink": "https://calendar.google.com/mock",
        "created": True,
    }


async def mock_list_tasks(user_id: str, max_results: int = 20) -> list[dict]:
    return [
        {"id": "task-001", "title": "Review PR #42", "due": "2026-04-10", "status": "needsAction", "priority": "high"},
        {"id": "task-002", "title": "Write demo script", "due": "2026-04-11", "status": "needsAction", "priority": "high"},
        {"id": "task-003", "title": "Update README", "due": "2026-04-12", "status": "needsAction", "priority": "low"},
    ]


async def mock_create_task(title: str, due: str = "", notes: str = "") -> dict:
    return {
        "id": "mock-task-new-001",
        "title": title,
        "due": due,
        "notes": notes,
        "created": True,
    }


async def mock_list_gmail_messages(user_id: str, max_results: int = 10, query: str = "") -> list[dict]:
    return [
        {
            "id": "msg-001",
            "snippet": "Hey, can we move the standup to 10am?",
            "from": "teammate@company.com",
            "subject": "Quick question about standup",
            "date": "2026-04-09",
            "unread": True,
        }
    ]


# ── Public API (real or mock, same interface) ─────────────────────────────────

async def get_calendar_events(user_id: str, max_results: int = 10) -> list[dict]:
    if MOCK_WORKSPACE_MCP:
        logger.info("[MOCK] Getting calendar events for user_id=%s", user_id)
        return await mock_get_calendar_events(user_id, max_results)
    # Real path: the ADK agent handles tool calls — this is used for direct calls
    logger.warning("Direct MCP calendar call not supported outside ADK agent context.")
    return []


async def get_tasks(user_id: str, max_results: int = 20) -> list[dict]:
    if MOCK_WORKSPACE_MCP:
        logger.info("[MOCK] Getting tasks for user_id=%s", user_id)
        return await mock_list_tasks(user_id, max_results)
    logger.warning("Direct MCP tasks call not supported outside ADK agent context.")
    return []


async def get_gmail_messages(user_id: str, max_results: int = 10, query: str = "") -> list[dict]:
    if MOCK_WORKSPACE_MCP:
        logger.info("[MOCK] Getting Gmail messages for user_id=%s", user_id)
        return await mock_list_gmail_messages(user_id, max_results, query)
    logger.warning("Direct MCP Gmail call not supported outside ADK agent context.")
    return []


def get_toolset():
    """
    Return the McpToolset for use inside ADK Agent definitions.
    Returns None when MOCK_WORKSPACE_MCP=true (ADK not needed for tests).
    """
    if MOCK_WORKSPACE_MCP:
        logger.info("[MOCK] Workspace MCP toolset skipped — mock mode active")
        return None
    try:
        return _get_mcp_toolset()
    except Exception as exc:
        logger.error("Failed to create Workspace MCP toolset: %s", exc)
        return None