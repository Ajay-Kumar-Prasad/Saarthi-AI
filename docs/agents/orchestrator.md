# Orchestrator Agent

## Overview
- Coordinates multi-domain execution across Saarthi agents.
- Runs domain agents in parallel and merges responses.
- Produces combined summary, action list, and conflict list.

## Responsibilities
- Select runners for work, health, learning, finance, social domains.
- Filter execution to requested `domains` when provided.
- Execute agents concurrently with `asyncio.gather`.
- Convert agent exceptions into `AgentResponse(status=error)` entries.
- Detect cross-domain conflicts from agent outputs.
- Build merged response payload for API clients.

## Inputs
- Runner: `run_orchestrator(message: str, user_id: str, domains: list[str] | None = None)`.
- `message`: user request.
- `user_id`: user identifier.
- `domains`: optional subset like `["learning", "work"]`.

## Outputs
- Returns a dictionary with keys:
- `summary`
- `agent_responses` (serialized `AgentResponse` list)
- `cross_domain_conflicts`
- `all_conflicts`
- `all_actions`

## Internal Flow
- Build `runners` map for all domains.
- Apply domain filter if `domains` is passed.
- Execute all selected runners concurrently.
- For each result:
- If exception -> build error `AgentResponse`.
- Else -> append agent response directly.
- Run `_detect_cross_domain_conflicts`:
- Low sleep + high work task load.
- Learning conflict text + work context.
- Aggregate summaries/conflicts/actions into final dict.

## Dependencies
- `agents.work_agent.run_work_agent`.
- `agents.learning_agent.run_learning_agent`.
- `agents.finance_agent.run_finance_agent`.
- Local stubs in this file for health/social (not real module imports).
- Shared schema: `db/schemas.py`.

## Example Usage
- API path in `main.py`: `POST /chat`
- Example body:
- `{"message":"Give me my day plan","user_id":"00000000-0000-0000-0000-000000000001","domains":["work","learning"]}`

## Current Status
- Partial.

## Limitations
- Uses stub functions for health and social domains.
- File contains stale instructional comments at top.
- Assumes each runner returns valid `AgentResponse`; no strict runtime type guard.

## Future Improvements
- Replace health/social stubs with real module integrations.
- Add strict response validation before aggregation.
- Expand cross-domain conflict rules.
- Separate orchestration logic from file-level migration comments.
