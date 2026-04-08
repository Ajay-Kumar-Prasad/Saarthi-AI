# Social Agent

## Overview
- Intended to manage social-domain capabilities in Saarthi AI.
- Expected to be called by orchestrator and `/social/chat` route.

## Responsibilities
- TODO: Not implemented in `agents/social_agent.py`.

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
- API path in `main.py`: `POST /social/chat`
- Example body:
- `{"message":"Any social events this week?","user_id":"00000000-0000-0000-0000-000000000001"}`
- TODO: Current agent module has no runnable function.

## Current Status
- Not implemented.

## Limitations
- `agents/social_agent.py` is empty.
- `main.py` imports `run_social_agent`, which is missing in module.

## Future Improvements
- Implement `run_social_agent(message, user_id) -> AgentResponse`.
- Add social data connectors and conflict logic.
- Add tests and endpoint-level validation.
