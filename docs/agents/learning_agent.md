# Learning Agent

## Overview
- Manages the learning domain in Saarthi AI.
- Handles resources, sessions, notes, goals, skill gap, flashcards, and learning paths.
- Serves as one domain agent that the orchestrator can call.

## Responsibilities
- Track learning resources and progress.
- Schedule study sessions and detect calendar conflicts.
- Save and retrieve study notes.
- Create and manage study goals.
- Analyze skill gaps for target roles.
- Create/review spaced-repetition flashcards.
- Create and view learning paths.
- Return normalized `AgentResponse` payloads.

## Inputs
- Primary runner: `run_learning_agent(message: str, user_id: str)`.
- Tool-level inputs include:
- `user_id` (required for all tool operations).
- Message-derived fields such as `title`, `resource_type`, `role_name`, `question`, `answer`, `path_id`.

## Outputs
- Returns `AgentResponse` (`db/schemas.py`) with:
- `agent` (string)
- `status` (`ok` | `error` | `partial`)
- `summary` (string)
- `conflicts` (list of strings)
- `actions_taken` (list of strings)
- `data` (optional dict)

## Internal Flow
- Validate `user_id`; return normalized error response if missing.
- Route request:
- Deterministic route (`route_learning_request`) for structured intents.
- Direct dispatch route for keyword-based handling.
- Execute relevant tool functions (`tool_*`) and parse JSON output.
- Normalize output via `normalize_agent_response` or construct `AgentResponse` directly.
- Return error `AgentResponse` on exceptions.

## Dependencies
- DB layer: `db/learning_db.py`.
- Tools: `tools/learning_tools.py`.
- Schemas: `db/schemas.py`.
- Optional ADK runtime: `google.adk.*`, `google.genai.types`.
- Session service: `InMemorySessionService`.

## Example Usage
- API path in `main.py`: `POST /learning/chat`
- Example body:
- `{"message":"What am I currently studying?","user_id":"00000000-0000-0000-0000-000000000001"}`

## Current Status
- Implemented.

## Limitations
- File mixes deterministic flows and large keyword routing logic in one module.
- ADK path exists, but runtime behavior primarily uses direct dispatch in `run_learning_agent`.
- Some behavior depends on external credentials/tokens and DB availability.

## Future Improvements
- Split intent routing into smaller modules.
- Add stronger schema validation for all parsed tool outputs.
- Reduce duplicate routing logic and centralize intent definitions.
- Add targeted tests for each deterministic intent path.
