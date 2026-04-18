"use client"

import type { WorkData, WorkTask as Task } from "@/lib/api"
import { FormEvent, useEffect, useState } from "react"
import { AlarmClock, ClipboardList, Flame, type LucideIcon } from "lucide-react"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { AgentResponse } from "@/types/agent"
import { fetchWorkStatus, postAgent } from "@/lib/api"

const USER_ID = "chjoshna145@gmail.com"

function normalizeStatus(status: unknown): Task["status"] {
  if (status === "pending") return "pending"
  if (status === "in_progress") return "in_progress"
  if (status === "completed") return "completed"
  return "pending"
}

function normalizeWorkData(raw: Record<string, unknown>): WorkData {
  return {
    tasks: Array.isArray(raw.tasks)
      ? raw.tasks.map((t) => {
          const task = t as Record<string, unknown>

          return {
            id: Number(task.id ?? 0),
            user_id: String(task.user_id ?? ""),
            title: String(task.title ?? ""),
            status: normalizeStatus(task.status),
            due_date: typeof task.due_date === "string" ? task.due_date : null,
            created_at: String(task.created_at ?? ""),
          }
        })
      : [],
    high_priority_tasks:
      typeof raw.high_priority_tasks === "number"
        ? raw.high_priority_tasks
        : 0,
    due_today:
      typeof raw.due_today === "number"
        ? raw.due_today
        : 0,
    insight:
      typeof raw.insight === "string"
        ? raw.insight
        : "",
  }
}

export default function WorkPage() {
  const [input, setInput] = useState("Show my work status")
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<AgentResponse<WorkData> | null>(null)

  useEffect(() => {
    runQuery("show my work status")
  }, [])

  async function runQuery(message: string) {
    setLoading(true)

    try {
      let result: AgentResponse<WorkData>

      if (message.toLowerCase().includes("status")) {
        result = await fetchWorkStatus(USER_ID)
      } else {
        const chatRes = await postAgent("/api/work/chat", {
          user_id: USER_ID,
          message,
        })

        const safeData = normalizeWorkData(
          (chatRes.data ?? {}) as Record<string, unknown>
        )

        result = {
          ...chatRes,
          data: safeData,
        }
      }

      setResponse(result)
    } catch {
      // ✅ SAFE FALLBACK (NO TYPE ERRORS)
      setResponse({
        agent: "work_agent",
        status: "error",
        summary: "Unable to fetch data.",
        conflicts: [],
        actions_taken: [],
        data: {
          tasks: [],
          high_priority_tasks: 0,
          due_today: 0,
          insight: "",
        },
      })
    } finally {
      setLoading(false)
    }
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const message = input.trim()
    if (!message || loading) return
    await runQuery(message)
  }

  const data: WorkData =
    response?.data ?? {
      tasks: [],
      high_priority_tasks: 0,
      due_today: 0,
      insight: "",
    }

  const tasks = data.tasks

  return (
    <div className="p-8 space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Work Agent Dashboard
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Tasks, meetings, and productivity insights
        </p>
      </div>

      {/* Stats */}
      {response && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="Total Tasks" value={tasks.length} Icon={ClipboardList} />
          <StatCard label="High Priority" value={data.high_priority_tasks} Icon={Flame} />
          <StatCard label="Due Today" value={data.due_today} Icon={AlarmClock} />
        </div>
      )}

      {/* Task List */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <p className="text-xs uppercase mb-3 text-gray-500 dark:text-gray-400">Your Tasks</p>

        {tasks.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No tasks found.</p>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800"
              >
                <p className="font-medium text-gray-900 dark:text-white">{task.title}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {task.status} •{" "}
                  {task.due_date ? task.due_date.slice(0, 10) : "No due date"}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chat */}
      <form
        onSubmit={onSubmit}
        className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
      >
        <p className="mb-2 text-sm text-gray-500 dark:text-gray-400">Ask Work Agent</p>

        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 px-4 py-2 rounded-lg text-sm"
          >
            {loading ? "Thinking..." : "Send"}
          </button>
        </div>
      </form>

      {/* Response Panel */}
      {response && (
        <AgentResponsePanel title="Work Agent" response={response} />
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  Icon,
}: {
  label: string
  value: number
  Icon: LucideIcon
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <div className="flex justify-between items-center mt-2">
        <p className="text-xl font-semibold text-gray-900 dark:text-white">{value}</p>
        <Icon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
      </div>
    </div>
  )
}
