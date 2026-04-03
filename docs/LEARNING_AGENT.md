# Learning Agent — Saarthi AI

> Member: Ajay Kumar Prasad | Domain: Learning

Your sub-agent manages books, courses, study schedules, notes, streaks, and learning goals.

---

## Files You Own

```
agents/learning_agent.py   ← THE AGENT — ADK definition + all tool functions
tools/learning_tools.py    ← MCP wrappers (Calendar + Notes)
db/learning_db.py          ← AlloyDB CRUD for learning domain
db/schema.sql              ← Shared schema (includes your 3 tables)
models/schemas.py          ← Pydantic models (AgentResponse contract)
tests/test_learning_agent.py ← Unit tests
main.py                    ← FastAPI routes for /learning/*
```

---

## Quick Start (Local)

```bash
# 1. Clone and enter the repo
cd Saarthi-AI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file
cp .env.example .env
# Set MOCK_MCP=true — no real MCP servers needed locally

# 4. Run the API
uvicorn main:app --reload --port 8080
```

**Test endpoints:**

```bash
# Health check
curl http://localhost:8080/health

# Natural language chat with Learning Agent
curl -X POST http://localhost:8080/learning/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What am I currently studying?", "user_id": "00000000-0000-0000-0000-000000000001"}'

# Schedule a study session
curl -X POST http://localhost:8080/learning/schedule \
  -H "Content-Type: application/json" \
  -d '{"message": "Schedule 1 hour of Python study for tomorrow", "user_id": "00000000-0000-0000-0000-000000000001"}'
```

---

## Run Tests

```bash
MOCK_MCP=true pytest tests/ -v
```

---

## How It Connects to the Orchestrator

Your `learning_agent` object is imported by Member 2 (Orchestrator) like this:

```python
# In agents/orchestrator.py (Member 2's file)
from agents.learning_agent import learning_agent

orchestrator = Agent(
    sub_agents=[..., learning_agent, ...]
)
```

Your agent **must** return a valid `AgentResponse` JSON — the orchestrator reads
`.conflicts` to detect cross-domain issues.

---

## Demo Scenario (for judges)

Input: *"I want to finish the GCP certification in 30 days"*

Expected agent flow:
1. `tool_get_learning_status` → sees GCP cert at 60%, 2h/week current pace
2. Calculates: needs ~8h/week to hit 100% in 30 days
3. `tool_schedule_study_session` × 4 → books 4 x 2h blocks this week
4. `tool_create_study_goal` → saves the 30-day goal to AlloyDB
5. Returns conflict if any block clashes with calendar events
6. Summary: *"I've scheduled 8 hours of GCP study this week across 4 sessions and saved your 30-day goal. You're currently 60% complete — on track if you hit 8h/week."*