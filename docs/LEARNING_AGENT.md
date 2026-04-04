# Learning Agent — Saarthi AI

> **Owner:** Ajay Kumar Prasad | **Domain:** Learning
> Part of the Saarthi AI multi-agent personal intelligence system.

---

## Table of Contents

1. [What This Agent Does](#1-what-this-agent-does)
2. [Files You Own](#2-files-you-own)
3. [How the Agent Works — Full Workflow](#3-how-the-agent-works--full-workflow)
4. [The 9 Tools — What Each One Does](#4-the-9-tools--what-each-one-does)
5. [The 3 Database Tables](#5-the-3-database-tables)
6. [MCP Tool Integrations](#6-mcp-tool-integrations)
7. [Conflict Detection Rules](#7-conflict-detection-rules)
8. [The AgentResponse Contract](#8-the-agentresponse-contract)
9. [How It Connects to the Orchestrator](#9-how-it-connects-to-the-orchestrator)
10. [Quick Start & Testing](#10-quick-start--testing)
11. [All API Endpoints](#11-all-api-endpoints)
12. [Demo Scenario for Judges](#12-demo-scenario-for-judges)

---

## 1. What This Agent Does

The Learning Agent is one of five sub-agents in Saarthi AI. Its job is to manage
everything related to the user's learning journey:

- Tracking **books, courses, articles, and videos** the user is studying
- **Scheduling study sessions** as calendar blocks (via Calendar MCP)
- **Saving and retrieving notes** from study sessions (via Notes MCP)
- Tracking **streaks, progress percentages, and weekly hours**
- Managing **long-term learning goals** (e.g. "finish GCP cert in 30 days")
- **Detecting conflicts** — when study blocks clash with other life events
- Answering **natural language questions** about learning history via AlloyDB AI

---

## 2. Files You Own

```
agents/learning_agent.py      ← THE AGENT — ADK definition + all 9 tool functions
tools/learning_tools.py       ← MCP wrappers for Calendar and Notes servers
db/learning_db.py             ← AlloyDB CRUD for your 3 tables
db/alloydb.py                 ← Shared DB connection + NL-to-SQL utility
db/schema.sql                 ← SQL for users + your 3 tables + seed data
models/schemas.py             ← Pydantic models (AgentResponse + Learning schemas)
tests/test_learning_agent.py  ← 10 unit tests (run with MOCK_MCP=true)
main.py                       ← FastAPI routes: /learning/chat, /learning/status, etc.
```

---

## 3. How the Agent Works — Full Workflow

This is what happens from the moment a user sends a message to the moment
the response is returned. Every step maps to real code in your files.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FULL REQUEST LIFECYCLE                       │
└─────────────────────────────────────────────────────────────────────┘

  USER MESSAGE
  "Schedule 1 hour of Python study for tomorrow"
         │
         ▼
┌─────────────────┐
│   main.py       │  POST /learning/chat
│   FastAPI       │  Receives the HTTP request
│   endpoint      │  Calls run_learning_agent(message, user_id)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  agents/learning_agent.py — run_learning_agent()                    │
│                                                                     │
│  Creates a Google ADK Runner with the learning_agent definition.    │
│  Passes the message + user_id as context.                           │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GOOGLE ADK — Agent reasoning loop                                  │
│                                                                     │
│  Gemini 2.0 Flash reads:                                            │
│    1. The LEARNING_AGENT_INSTRUCTION (the system prompt)            │
│    2. The user message                                              │
│    3. The docstrings of all 9 tool functions                        │
│                                                                     │
│  It decides: "This needs tool_schedule_study_session"               │
│  (because the docstring says: use when user says 'schedule study')  │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  tool_schedule_study_session() — inside learning_agent.py           │
│                                                                     │
│  Step 1: find_free_slot(user_id, date="tomorrow", duration=60)      │
│    → calls tools/learning_tools.py                                  │
│    → GET /events from Calendar MCP (or mock)                        │
│    → scans existing events, finds 6:00am is free                    │
│                                                                     │
│  Step 2: create_study_calendar_event(...)                           │
│    → POST /events/create to Calendar MCP (or mock)                  │
│    → returns { event_id: "cal-001", start: "06:00" }               │
│                                                                     │
│  Step 3: create_study_session(session)                              │
│    → calls db/learning_db.py                                        │
│    → INSERT INTO study_sessions ... (saved to AlloyDB forever)      │
│                                                                     │
│  Returns JSON: { conflict: false, session: {...}, calendar: {...} } │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ADK reasoning loop — conflict check                                │
│                                                                     │
│  Gemini reads the tool result and checks the instruction's          │
│  conflict rules. In this case:                                      │
│    - No overlap detected → conflicts[] stays empty                  │
│    - Streak is 18 days → adds a positive note to summary            │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Agent builds AgentResponse JSON (the output contract)              │
│                                                                     │
│  {                                                                  │
│    "agent": "learning_agent",                                       │
│    "status": "ok",                                                  │
│    "summary": "Scheduled 1hr Python study tomorrow at 6:00am.      │
│                You're on an 18-day streak — keep it up!",           │
│    "conflicts": [],                                                 │
│    "actions_taken": [                                               │
│      "Created calendar event: Study: Python Crash Course",         │
│      "Saved session to AlloyDB study_sessions table"               │
│    ],                                                               │
│    "data": { "session_id": "...", "streak_days": 18 }              │
│  }                                                                  │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
  RESPONSE returned to user via FastAPI
  (or to the Orchestrator if called as a sub-agent)
```

---

## 4. The 9 Tools — What Each One Does

These are Python `async def` functions inside `agents/learning_agent.py`.
Google ADK reads their **docstrings** to decide which one to call.
You never hardcode "if user says X, call tool Y" — Gemini reasons about it.

| Tool | When the model calls it | What it does internally |
|---|---|---|
| `tool_get_learning_status` | "What am I studying?" / any status question | Fetches all resources, sessions, goals, weekly hours, streak from AlloyDB |
| `tool_add_learning_resource` | "Add Atomic Habits to my list" / "I started a new course" | Inserts a row into `learning_resources` table |
| `tool_update_progress` | "I'm on page 280" / "I finished 70% of the course" | Updates `progress_pct` and `current_page` in AlloyDB |
| `tool_schedule_study_session` | "Schedule study time for tomorrow" | Finds free calendar slot → books Calendar MCP event → saves to `study_sessions` |
| `tool_log_study_note` | "Save this note" / "I learned that..." | POSTs note content to Notes MCP server |
| `tool_get_notes` | "Show my notes on Python" / "What did I write about X" | GETs notes from Notes MCP, filtered by resource |
| `tool_mark_session_done` | "Done with today's study" / "Completed my session" | Sets `completed = true` in `study_sessions` table |
| `tool_query_learning_history` | "How many hours last month?" / "Which courses have I paused?" | Sends natural language to AlloyDB AI → auto-generates SQL → returns results |
| `tool_create_study_goal` | "I want to finish the GCP cert in 30 days" | Inserts a row into `study_goals` table |

### Why docstrings matter

ADK passes each tool's docstring to Gemini as its "description". This is
how the model decides which tool to call. If you ever add a new tool,
write a clear docstring that explains exactly what phrases should trigger it:

```python
async def tool_update_progress(user_id, resource_id, progress_pct, current_page=0) -> str:
    """
    Update the user's progress on a book or course.
    Use when the user says 'I finished chapter X', 'I'm at page Y',
    'I completed 70% of the course'.
    ...
    """
```

---

## 5. The 3 Database Tables

All in AlloyDB (Postgres). Defined in `db/schema.sql`.
All CRUD operations are in `db/learning_db.py`.

### `learning_resources` — books, courses, articles being tracked

```
id              UUID (primary key)
user_id         UUID (foreign key → users)
title           TEXT  — e.g. "Python Crash Course"
resource_type   TEXT  — book | course | article | video | podcast
url             TEXT  — optional link
author          TEXT  — optional
status          TEXT  — not_started | in_progress | completed | paused
progress_pct    INT   — 0 to 100
total_pages     INT   — for books
current_page    INT   — for books
notes           TEXT  — free-form notes
tags            TEXT[] — e.g. {python, programming}
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

### `study_sessions` — scheduled study blocks

```
id                UUID (primary key)
user_id           UUID (foreign key → users)
resource_id       UUID (foreign key → learning_resources)
title             TEXT  — display name, e.g. "Study: Python Crash Course"
scheduled_at      TIMESTAMPTZ — when the session is booked
duration_minutes  INT   — default 60
calendar_event_id TEXT  — Google Calendar event ID returned by MCP
completed         BOOLEAN — false until user marks it done
notes             TEXT  — what was studied in this session
created_at        TIMESTAMPTZ
```

### `study_goals` — long-term learning objectives

```
id                  UUID (primary key)
user_id             UUID (foreign key → users)
resource_id         UUID (foreign key → learning_resources, nullable)
title               TEXT  — e.g. "Complete GCP cert before demo day"
target_date         DATE  — deadline
weekly_hours_target NUMERIC — hours/week needed to hit the goal
progress_pct        INT   — 0 to 100
status              TEXT  — active | paused | completed
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

---

## 6. MCP Tool Integrations

Defined in `tools/learning_tools.py`. Two MCP servers are used.

### Calendar MCP

Used to check existing events and create study blocks.

```
find_free_slot(user_id, date, duration_minutes)
  → GET  {MCP_CALENDAR_URL}/events?user_id=...&date=...
  → Scans busy slots, returns first available start time

create_study_calendar_event(user_id, title, start_time, duration_minutes)
  → POST {MCP_CALENDAR_URL}/events/create
  → Returns { event_id, html_link, start, end }
```

### Notes MCP

Used to save and retrieve study notes.

```
save_learning_note(user_id, resource_title, note_content, tags)
  → POST {MCP_NOTES_URL}/notes/create
  → Returns { note_id, saved: true }

get_learning_notes(user_id, resource_title)
  → GET  {MCP_NOTES_URL}/notes?user_id=...&tag=learning
  → Returns list of note objects
```

### Running without real MCP servers

Set `MOCK_MCP=true` in your `.env`. Every MCP function returns realistic
fake data so you can test the full agent flow locally without credentials.
AlloyDB is still real — only the MCP calls are mocked.

---

## 7. Conflict Detection Rules

The agent's instruction tells Gemini to check these rules after every action
and add violations to the `conflicts[]` array in the response.

```
Rule 1 — Scheduling clash
  IF a study session overlaps an existing calendar event
  THEN flag: "Study block on {DATE} at {TIME} overlaps with {EVENT_NAME}"

Rule 2 — Under-studying
  IF weekly hours studied < 50% of the user's active goal target
  THEN flag: "Only {X}h studied this week, goal requires {Y}h/week"

Rule 3 — Stalled resource
  IF a resource has status='in_progress' but progress unchanged for 30+ days
  THEN flag: "No progress on '{TITLE}' for 30+ days — consider resuming or pausing"

Rule 4 — Goal deadline at risk
  IF a goal's target_date is within 7 days AND progress_pct < 80
  THEN flag: "'{TITLE}' is due in {N} days but only {X}% complete"
```

These conflict strings are read by the **Orchestrator** (Member 2's code)
alongside conflicts from the Work, Health, Finance, and Social agents to
generate the cross-domain "Am I overcommitting this week?" answer.

**Important:** Make your conflict strings specific. Include dates, titles,
and numbers. `"Study block on 2026-04-10 at 6am overlaps with standup at 8:30am"`
is useful. `"conflict detected"` is not.

---

## 8. The AgentResponse Contract

Every sub-agent in Saarthi AI must return this exact schema.
Defined in `models/schemas.py`. The Orchestrator depends on it.

```python
class AgentResponse(BaseModel):
    agent:          str           # always "learning_agent"
    status:         AgentStatus   # "ok" | "error" | "partial"
    summary:        str           # human-readable paragraph
    conflicts:      list[str]     # flagged issues (can be empty)
    actions_taken:  list[str]     # what the agent did
    data:           dict | None   # raw structured data for orchestrator
```

### Example — successful schedule

```json
{
  "agent": "learning_agent",
  "status": "ok",
  "summary": "Scheduled 1 hour of Python study tomorrow at 6:00am. You have an 18-day streak — keep it going!",
  "conflicts": [],
  "actions_taken": [
    "Found free slot at 6:00am on 2026-04-05",
    "Created calendar event: Study: Python Crash Course",
    "Saved session to AlloyDB study_sessions table"
  ],
  "data": {
    "session_id": "uuid-here",
    "scheduled_at": "2026-04-05T06:00:00+05:30",
    "streak_days": 18,
    "weekly_hours_studied": 3.5
  }
}
```

### Example — with conflicts

```json
{
  "agent": "learning_agent",
  "status": "ok",
  "summary": "Scheduled study session but flagged 2 issues for your attention.",
  "conflicts": [
    "Study block on 2026-04-10 at 6am overlaps with standup at 6:30am",
    "GCP certification due in 5 days but only 60% complete"
  ],
  "actions_taken": [
    "Fetched upcoming study sessions",
    "Checked active goals against target dates"
  ],
  "data": {
    "goal_progress": 60,
    "days_until_deadline": 5
  }
}
```

---

## 9. How It Connects to the Orchestrator

Member 2 imports your agent object directly. You don't need to do anything
special — just make sure `learning_agent` is importable from
`agents/learning_agent.py`.

```python
# In agents/orchestrator.py — Member 2's file
from agents.learning_agent import learning_agent

orchestrator = Agent(
    name="lifeos_orchestrator",
    model="gemini-2.0-flash",
    sub_agents=[
        work_agent,
        health_agent,
        finance_agent,
        learning_agent,   # ← your agent plugs in here
        social_agent,
    ]
)
```

### What happens in a cross-domain query

When the user asks "Am I overcommitting this week?", the Orchestrator fires
all 5 sub-agents in parallel using `asyncio.gather`. Your agent returns its
`AgentResponse`. The Orchestrator collects all 5 responses and combines the
`conflicts[]` arrays from each agent into a single holistic answer.

```
Work Agent     → conflicts: ["8 tasks due today, 3 back-to-back meetings"]
Health Agent   → conflicts: ["Only 5.8hrs avg sleep this week"]
Finance Agent  → conflicts: []
Learning Agent → conflicts: ["GCP cert due in 5 days, only 60% done"]  ← yours
Social Agent   → conflicts: ["Friend's birthday tomorrow, no reminder set"]

Orchestrator   → "Yes, you're overcommitted. Here's what to adjust..."
```

---

## 10. Quick Start & Testing

### Local setup

```bash
cd Saarthi-AI
pip install -r requirements.txt
cp .env.example .env          # MOCK_MCP=true is already set
export $(grep -v '^#' .env | xargs)
uvicorn main:app --reload --port 8080
```

### Run tests

```bash
MOCK_MCP=true pytest tests/ -v
```

All 10 tests should pass. They mock the AlloyDB connection and use
`MOCK_MCP=true` so no external services are needed.

### Manual curl tests

```bash
# 1. Health check
curl http://localhost:8080/health

# 2. See what the demo user is studying
curl -X POST http://localhost:8080/learning/status \
  -H "Content-Type: application/json" \
  -d '{"user_id": "00000000-0000-0000-0000-000000000001"}'

# 3. Natural language chat
curl -X POST http://localhost:8080/learning/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What am I currently studying?",
       "user_id": "00000000-0000-0000-0000-000000000001"}'

# 4. Schedule a session
curl -X POST http://localhost:8080/learning/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Schedule 1 hour of Python study for tomorrow",
       "user_id": "00000000-0000-0000-0000-000000000001"}'

# 5. Add a new resource
curl -X POST http://localhost:8080/learning/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Add Atomic Habits by James Clear to my reading list",
       "user_id": "00000000-0000-0000-0000-000000000001"}'

# 6. AlloyDB AI natural language query
curl -X POST http://localhost:8080/learning/query \
  -H "Content-Type: application/json" \
  -d '{"message": "How many hours have I studied this week?",
       "user_id": "00000000-0000-0000-0000-000000000001"}'
```

---

## 11. All API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe for Cloud Run |
| POST | `/learning/chat` | Main natural language interface |
| POST | `/learning/status` | Quick snapshot (no LLM call) |
| POST | `/learning/add-resource` | Natural language resource addition |
| POST | `/learning/schedule` | Natural language scheduling |
| POST | `/learning/query` | AlloyDB AI NL query over history |

---

## 12. Demo Scenario for Judges

This is the exact interaction to rehearse for demo day. It hits every
judging criterion in under 60 seconds.

**Input:** `"I want to finish the GCP certification in 30 days"`

### What happens internally

```
Step 1 → tool_get_learning_status
         Fetches from AlloyDB:
           GCP cert: in_progress, 60% complete
           Current pace: ~2h/week studied
           Active sessions: 1 booked this week

Step 2 → Agent reasons:
           Needs ~8h/week to reach 100% in 30 days
           Currently doing 2h/week — needs 4x increase

Step 3 → tool_create_study_goal
         Saves to AlloyDB study_goals:
           title: "Complete GCP certification"
           target_date: 30 days from today
           weekly_hours_target: 8.0

Step 4 → tool_schedule_study_session × 4
         Books 4 × 2hr blocks this week via Calendar MCP
         Checks for conflicts with existing events each time
         Saves all 4 to study_sessions table in AlloyDB

Step 5 → Conflict check
         If any block overlaps an existing event:
           conflicts: ["Study block on DATE overlaps with EVENT"]
         Otherwise:
           conflicts: []
```

### Expected AgentResponse

```json
{
  "agent": "learning_agent",
  "status": "ok",
  "summary": "Goal saved: complete GCP certification in 30 days. I've scheduled 4 study sessions this week totalling 8 hours — Mon, Wed, Fri at 6am and Sat at 10am. You're currently 60% complete. At 8h/week you'll finish with 3 days to spare.",
  "conflicts": [],
  "actions_taken": [
    "Created study goal: Complete GCP certification (target: 30 days)",
    "Scheduled 4 study sessions: Mon 6am, Wed 6am, Fri 6am, Sat 10am",
    "Saved all sessions to AlloyDB"
  ],
  "data": {
    "goal_id": "uuid-here",
    "sessions_scheduled": 4,
    "weekly_hours_target": 8.0,
    "current_progress_pct": 60,
    "days_until_target": 30
  }
}
```

### What judges see

An agent that reasons about a goal, calculates what's needed, takes multiple
actions in sequence, checks for conflicts, and returns a specific actionable
plan — all from one natural language sentence. That is the difference between
a chatbot and an agent.

---

*Saarthi AI — सारथी | Because your learning journey deserves a guide, not nine apps.*