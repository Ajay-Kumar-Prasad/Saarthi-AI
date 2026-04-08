# Work Agent

## Overview
- Manages the work domain in Saarthi AI.
- Aggregates tasks, calendar, and unread email context.
- Produces domain conflicts and structured work data for orchestrator consumption.

## Responsibilities
- Fetch task summary from Workspace MCP wrapper.
- Fetch calendar summary and detect back-to-back meetings.
- Fetch unread Gmail summary.
- Detect work conflicts (overload, heavy meetings, inbox pressure).
- Route response focus by message intent (`task`, `meeting/calendar`, `email`, fallback full summary).

## Inputs
- Runner: `run_work_agent(message: str, user_id: str)`.
- Internal fetches use:
- `get_tasks(user_id, max_results=20)`
- `get_calendar_events(user_id, max_results=10)`
- `get_gmail_messages(user_id, max_results=10, query="is:unread")`

## Outputs
- Returns `AgentResponse` (`db/schemas.py`) with:
- `agent="work_agent"`
- `status` (`ok` | `partial` | `error`)
- `summary` intent-focused or full status summary
- `conflicts` filtered by intent or full conflict list
- `actions_taken` based on selected intent
- `data` containing tasks/calendar/email fields

## Internal Flow
- Validate `user_id`; return error response when missing.
- Fetch tasks/calendar/gmail concurrently with `asyncio.gather`.
- Convert per-source exceptions into partial fallback data and reasons.
- Build full conflict list using `_detect_work_conflicts`.
- Route summary/data by message intent:
- `task` -> task-focused output.
- `meeting` or `calendar` -> calendar-focused output.
- `email` -> inbox-focused output.
- Else -> full summary behavior.
- Attach partial notes when any source failed.

## Dependencies
- Schemas: `db/schemas.py`.
- Workspace MCP wrapper: `tools/workspace_mcp/client.py`.
- Optional ADK agent/toolset: `google.adk.agents.Agent`, `tools.workspace_mcp.client.get_toolset`.

## Example Usage
- API path in `main.py`: `POST /work/chat`
- Example body:
- `{"message":"Show my meetings today","user_id":"00000000-0000-0000-0000-000000000001"}`

## Current Status
- Partial.

## Limitations
- Real direct MCP calls in `tools/workspace_mcp/client.py` return empty lists unless mock mode is enabled.
- ADK agent object is defined, but runner path in `run_work_agent` uses direct tool wrappers.
- Intent routing uses simple keyword matching only.

## Future Improvements
- Implement real direct MCP execution path for non-mock mode.
- Add richer intent detection and entity extraction.
- Add action tools (create/complete task, schedule event) in runner path.
- Add dedicated tests for intent-specific responses and conflict filtering.
