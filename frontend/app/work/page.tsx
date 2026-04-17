"use client"

import type { WorkData, WorkTask as Task } from "@/lib/api"
import { FormEvent, useEffect, useState } from "react"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { AgentResponse } from "@/types/agent"
import { fetchWorkStatus, postAgent } from "@/lib/api"
import { ClipboardList, Flame, Clock } from "lucide-react"

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
      ? raw.tasks.map((t: any) => ({
          id: Number(t?.id ?? 0),
          user_id: String(t?.user_id ?? ""),
          title: String(t?.title ?? ""),
          status: normalizeStatus(t?.status),
          due_date: t?.due_date ?? null,
          created_at: String(t?.created_at ?? ""),
        }))
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
        <h1 className="text-2xl font-semibold text-white">
          Work Agent Dashboard
        </h1>
        <p className="text-sm text-gray-400">
          Tasks, meetings, and productivity insights
        </p>
      </div>

      {/* Stats */}
      {response && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="Total Tasks" value={tasks.length} icon={ClipboardList} />
          <StatCard label="High Priority" value={data.high_priority_tasks} icon={Flame} />
          <StatCard label="Due Today" value={data.due_today} icon={Clock} />
        </div>
      )}

      {/* Task List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <p className="text-gray-400 text-xs uppercase mb-3">Your Tasks</p>

        {tasks.length === 0 ? (
          <p className="text-gray-600 text-sm">No tasks found.</p>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="p-3 bg-gray-800 rounded-lg border border-gray-700"
              >
                <p className="text-white font-medium">{task.title}</p>
                <p className="text-gray-400 text-xs">
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
        className="bg-gray-900 border border-gray-800 rounded-xl p-4"
      >
        <p className="text-sm text-gray-400 mb-2">Ask Work Agent</p>

        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 px-3 py-2 rounded-lg text-sm"
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
  icon,
}: {
  label: string
  value: number
  icon: React.ElementType
}) {
  const Icon = icon

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-gray-400 text-xs">{label}</p>

      <div className="flex justify-between items-center mt-2">
        <p className="text-white text-xl font-semibold">{value}</p>

        <span className="text-indigo-500">
          <Icon size={20} />
        </span>
      </div>
    </div>
  )
}