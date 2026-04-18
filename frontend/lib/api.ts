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

export type WorkTask = {
  id: number
  user_id: string
  title: string
  status: "pending" | "in_progress" | "completed"
  due_date?: string | null
  created_at: string
}

export type WorkData = {
  tasks: WorkTask[]
  high_priority_tasks: number
  due_today: number
  insight: string
}

type HealthStatusData = {
  daily_metrics: {
    date: string
    total_steps?: number | null
    total_calories?: number | null
    active_minutes?: number | null
    resting_heart_rate?: number | null
  }[]
  activity_sessions: Record<string, unknown>[]
}

const USER_ID = "chjoshna145@gmail.com"

async function requestAgent(
  path: string,
  init?: RequestInit
): Promise<AgentResponse<JsonRecord>> {
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
      return {
        agent: "frontend_proxy",
        status: "error",
        summary: "Invalid backend response format.",
        conflicts: [],
        actions_taken: [],
        data: {}, //  always object
      }
    }

    //  force data to always be object
    const safeData =
      payload.data && typeof payload.data === "object"
        ? payload.data
        : {}

    return {
      ...payload,
      data: safeData,
    } as AgentResponse<JsonRecord>
  } catch (error) {
    return {
      agent: "frontend_proxy",
      status: "error",
      summary: error instanceof Error ? error.message : "Request failed.",
      conflicts: [],
      actions_taken: [],
      data: {}, // consistent
    }
  }
}

export async function postAgent(path: string, body: JsonRecord): Promise<AgentResponse<JsonRecord>> {
  return requestAgent(path, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function getAgent(path: string): Promise<AgentResponse<JsonRecord>> {
  return requestAgent(path, { method: "GET" })
}

export async function deleteAgent(path: string): Promise<AgentResponse<JsonRecord>> {
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

export async function fetchLearningStatus(userId: string): Promise<AgentResponse<LearningStatus>> {
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

export async function fetchHealthStatus(
  userId?: string,
  days = 7
): Promise<AgentResponse<HealthStatusData>> {
  const body: JsonRecord = { days }
  if (userId && userId.trim()) {
    body.user_id = userId
  }

  const response = await postAgent("/api/health/status", body)

  // unwrap properly
  const raw = (response.data?.health_summary ?? {}) as Record<string, unknown>

  return {
    ...response,
    data: {
      daily_metrics: Array.isArray(raw.daily_metrics)
        ? (raw.daily_metrics as HealthStatusData["daily_metrics"])
        : [],
      activity_sessions: Array.isArray(raw.activity_sessions)
        ? (raw.activity_sessions as HealthStatusData["activity_sessions"])
        : [],
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
function normalizeStatus(status: unknown): "pending" | "in_progress" | "completed" {
  if (status === "pending") return "pending"
  if (status === "in_progress") return "in_progress"
  if (status === "completed") return "completed"
  return "pending" // fallback (safe default)
}
export async function fetchWorkStatus(
  userId: string
): Promise<AgentResponse<WorkData>> {
  const response = await postAgent("/api/work/chat", {
    user_id: userId,
    message: "show my work status",
  })

  const raw = response.data as Record<string, unknown>

  //  sanitize tasks properly (not blindly cast)
  const tasks: WorkTask[] = Array.isArray(raw?.tasks)
    ? raw.tasks.map((t: any) => ({
        id: Number(t?.id ?? 0),
        user_id: String(t?.user_id ?? ""),
        title: String(t?.title ?? ""),
        status: normalizeStatus(t?.status),
        due_date: t?.due_date ?? null,
        created_at: String(t?.created_at ?? ""),
      }))
    : []

  const data: WorkData = {
    tasks,
    high_priority_tasks:
      typeof raw?.high_priority_tasks === "number"
        ? raw.high_priority_tasks
        : 0,
    due_today:
      typeof raw?.due_today === "number"
        ? raw.due_today
        : 0,
    insight:
      typeof raw?.insight === "string"
        ? raw.insight
        : "",
  }

  return {
    ...response,
    data,
  }
}

export async function workChat(message: string) {
  return postAgent("/api/work/chat", {
    user_id: USER_ID,
    message,
  })
}

export async function createWorkTask(
  userId: string,
  title: string
) {
  return postAgent("/api/work/tasks/create", {
    user_id: userId,
    message: title,
  })
}