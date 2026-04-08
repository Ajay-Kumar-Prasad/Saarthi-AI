# Health Agent

## Overview
- Intended to manage health-domain capabilities in Saarthi AI.
- Expected to be called by orchestrator and `/health/chat` route.

## Responsibilities
- TODO: Not implemented in `agents/health_agent.py`.

## Inputs
- TODO.

## Outputs
- Intended contract is `AgentResponse` from `db/schemas.py`.
- TODO: No concrete implementation.

## Internal Flow
- Not implemented.

## Dependencies
- TODO.

## Example Usage
- API path in `main.py`: `POST /health/chat`
- Example body:
- `{"message":"How is my health today?","user_id":"00000000-0000-0000-0000-000000000001"}`
- TODO: Current agent module has no runnable function.

## Current Status
- Not implemented.

## Limitations
- `agents/health_agent.py` is empty.
- `main.py` imports `run_health_agent`, which is missing in module.

## Future Improvements
- Implement `run_health_agent(message, user_id) -> AgentResponse`.
- Add health DB/tool integrations.
- Add tests and endpoint-level validation.
