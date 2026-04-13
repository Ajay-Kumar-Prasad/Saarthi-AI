import { AgentResponse, fallbackAgentResponse, isAgentResponse } from "@/types/agent"

type JsonRecord = Record<string, unknown>

export type Resource = {
  id: string
  title: string
  resource_type: string
  author?: string | null
  status: string
  progress_pct: number
  tags: string[]
}

export type Session = {
  id: string
  title: string
  scheduled_at: string
  duration_minutes: number
  calendar_event_id?: string | null
  resource_type?: string
  resource_title?: string
}

export type Goal = {
  id: string
  title: string
  weekly_hours_target: number
  progress_pct: number
  target_date?: string | null
  status: string
}

export type LearningStatus = {
  resources: Resource[]
  upcoming_sessions: Session[]
  active_goals: Goal[]
  weekly_hours_studied: number
  streak_days: number
}

export type HealthSummary = {
  daily_metrics: Array<{
    date: string
    total_steps?: number | null
    total_calories?: number | null
    active_minutes?: number | null
    resting_heart_rate?: number | null
  }>
  activity_sessions: Array<Record<string, unknown>>
}

const USER_ID = "00000000-0000-0000-0000-000000000001"

async function requestAgent(path: string, init?: RequestInit): Promise<AgentResponse<JsonRecord | null>> {
  try {
    const response = await fetch(path, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    })
    const payload = (await response.json()) as unknown
    if (!isAgentResponse(payload)) {
      return fallbackAgentResponse("frontend_proxy", "Invalid backend response format.")
    }
    return payload as AgentResponse<JsonRecord | null>
  } catch (error) {
    return fallbackAgentResponse(
      "frontend_proxy",
      error instanceof Error ? error.message : "Request failed.",
    )
  }
}

export async function postAgent(path: string, body: JsonRecord): Promise<AgentResponse<JsonRecord | null>> {
  return requestAgent(path, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function getAgent(path: string): Promise<AgentResponse<JsonRecord | null>> {
  return requestAgent(path, { method: "GET" })
}

export async function deleteAgent(path: string): Promise<AgentResponse<JsonRecord | null>> {
  return requestAgent(path, { method: "DELETE" })
}

function toResourceArray(value: unknown): Resource[] {
  return Array.isArray(value) ? (value as Resource[]) : []
}

function toSessionArray(value: unknown): Session[] {
  return Array.isArray(value) ? (value as Session[]) : []
}

function toGoalArray(value: unknown): Goal[] {
  return Array.isArray(value) ? (value as Goal[]) : []
}

export async function fetchLearningStatus(userId: string): Promise<AgentResponse<LearningStatus | null>> {
  const response = await postAgent("/api/learning/status", { user_id: userId })
  const data = (response.data ?? {}) as Partial<LearningStatus>
  return {
    ...response,
    data: {
      resources: toResourceArray(data.resources),
      upcoming_sessions: toSessionArray(data.upcoming_sessions),
      active_goals: toGoalArray(data.active_goals),
      weekly_hours_studied: typeof data.weekly_hours_studied === "number" ? data.weekly_hours_studied : 0,
      streak_days: typeof data.streak_days === "number" ? data.streak_days : 0,
    },
  }
}

export async function fetchHealthStatus(userId: string, days = 7): Promise<AgentResponse<HealthSummary | null>> {
  const response = await postAgent("/api/health/status", { user_id: userId, days })
  const data = (response.data ?? {}) as Partial<HealthSummary>
  return {
    ...response,
    data: {
      daily_metrics: Array.isArray(data.daily_metrics) ? data.daily_metrics : [],
      activity_sessions: Array.isArray(data.activity_sessions) ? data.activity_sessions : [],
    },
  }
}

export const api = {
  learning: {
    chat: (message: string) => postAgent("/api/learning/chat", { user_id: USER_ID, message }),

    skillGap: async (role: string) => {
      const res = await postAgent("/api/learning/skill-gap", {
        user_id: USER_ID,
        role,
      })
      return {
        summary: String(res.summary ?? ""),
        data: (res.data ?? {}) as Record<string, unknown>,
      }
    },

    flashcards: () => postAgent("/api/learning/flashcards", { user_id: USER_ID }),

    path: (message: string) => postAgent("/api/learning/path", { user_id: USER_ID, message }),

    saveNote: (resource: string, note: string) =>
      postAgent("/api/learning/notes", {
        user_id: USER_ID,
        resource,
        note,
      }),
  },
}
