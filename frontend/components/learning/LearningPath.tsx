"use client"
import { useState } from "react"
import { api } from "@/lib/api"


type Step = {
  id?: string
  title: string
  status: string
  why_this: string
  step_order: number
  estimated_hours?: number
}

const STATUS_CYCLE: Record<string, string> = {
  pending:     "in_progress",
  in_progress: "completed",
  completed:   "pending",
  skipped:     "pending",
}

const STATUS_STYLE: Record<string, string> = {
  completed:   "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800 text-green-700 dark:text-green-400",
  in_progress: "bg-indigo-50 dark:bg-indigo-950/30 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-400",
  pending:     "bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400",
  skipped:     "bg-gray-50 dark:bg-gray-800/30 border-gray-200 dark:border-gray-700 text-gray-400",
}

const STATUS_ICON: Record<string, string> = {
  completed: "✓", in_progress: "◎", pending: "○", skipped: "—",
}

async function updateStep(pathId: string, stepId: string, status: string) {
  return api.learning.chat(`Update learning path step: path_id=${pathId}, step_id=${stepId}, status=${status}`)
}

export default function LearningPath() {
  const [steps, setSteps] = useState<Step[]>([])
  const [loading, setLoading] = useState(false)
  const [role, setRole] = useState("")
  const [pathTitle, setPathTitle] = useState("")
  const [pathId, setPathId] = useState<string | null>(null)
  const [updatingStep, setUpdatingStep] = useState<number | null>(null)

  async function create() {
    if (!role.trim()) return
    setLoading(true)
    try {
      const res = await api.learning.path(`I want to become a ${role}, create a roadmap for me`)
      const raw = res?.data as Record<string, unknown>
      const pathData = raw?.learning_path as Record<string, unknown>
      const path = pathData?.path as Record<string, unknown>
      setPathTitle(String(path?.title ?? `Road to ${role}`))
      setPathId(String(path?.id ?? ""))
      setSteps(Array.isArray(pathData?.steps) ? pathData.steps as Step[] : [])
    } finally { setLoading(false) }
  }

  async function loadExisting() {
    setLoading(true)
    try {
      const res = await api.learning.path("Show my learning path")
      const raw = res?.data as Record<string, unknown>
      const paths = raw?.paths as Record<string, unknown>[]
      if (!paths?.length) return

      const latest = paths[0]
      const pathIdVal = String(latest?.id ?? "")
      const res2 = await api.learning.path(`Show my learning path id=${pathIdVal}`)
      const raw2 = res2?.data as Record<string, unknown>
      const pathData = raw2?.path as Record<string, unknown> ?? {}

      setPathTitle(String(pathData?.title ?? "My Learning Path"))
      setPathId(String(pathData?.id ?? ""))
      setSteps(Array.isArray(pathData?.steps) ? pathData.steps as Step[] : [])
    } finally { setLoading(false) }
  }

  async function cycleStepStatus(step: Step, idx: number) {
    if (!pathId || !step.id) return
    const currentStatus = step.status ?? "pending"
    const nextStatus = STATUS_CYCLE[currentStatus] ?? "in_progress"
    setUpdatingStep(idx)
    try {
      await updateStep(pathId, step.id, nextStatus)
      setSteps((prev) => prev.map((s, i) => i === idx ? { ...s, status: nextStatus } : s))
    } finally {
      setUpdatingStep(null)
    }
  }

  const completed = steps.filter((s) => s.status === "completed").length
  const progress = steps.length > 0 ? Math.round((completed / steps.length) * 100) : 0

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <h3 className="text-gray-900 dark:text-white font-semibold mb-1">Learning Path</h3>
      <p className="text-gray-500 text-xs mb-4">Build a structured roadmap toward a career goal</p>

      <div className="flex gap-2 mb-4">
        <input value={role} onChange={(e) => setRole(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && create()}
          placeholder="e.g. Data Engineer"
          className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white text-sm rounded-lg px-3 py-2 placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors"
        />
        <button onClick={create} disabled={loading || !role.trim()}
          className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors font-medium">
          {loading ? "Building…" : "Build"}
        </button>
        <button onClick={loadExisting} disabled={loading}
          className="px-3 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 text-gray-700 dark:text-white text-sm rounded-lg transition-colors">
          Load
        </button>
        {steps.length > 0 && (
          <button onClick={() => { setSteps([]); setPathId(null); setPathTitle("") }}
            className="px-3 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 text-sm rounded-lg transition-colors">
            ✕
          </button>
        )}
      </div>

      {steps.length > 0 && (
        <div className="space-y-3">
          {pathTitle && (
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <p className="text-gray-700 dark:text-gray-300 text-sm font-medium">{pathTitle}</p>
                <span className="text-xs text-gray-500">
                  {completed}/{steps.length} done · {progress}%
                </span>
              </div>
              <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {steps.map((s, i) => {
            const status = s.status ?? "pending"
            return (
              <div key={i}
                className={`border rounded-xl p-3.5 transition-colors ${STATUS_STYLE[status] ?? STATUS_STYLE.pending} ${s.id && pathId ? "cursor-pointer hover:opacity-80" : ""}`}
                onClick={() => s.id && pathId && cycleStepStatus(s, i)}
                title={s.id && pathId ? "Click to advance status" : undefined}
              >
                <div className="flex items-start gap-2.5">
                  <span className={`font-bold text-sm mt-0.5 w-5 shrink-0 text-center transition-opacity ${updatingStep === i ? "opacity-30" : ""}`}>
                    {updatingStep === i ? "…" : (STATUS_ICON[status] ?? "○")}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-sm">{s.title}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        {s.estimated_hours && (
                          <span className="text-xs opacity-60">{s.estimated_hours}h</span>
                        )}
                        <span className={`text-xs px-2 py-0.5 rounded-full border capitalize
                          ${status === "completed"   ? "border-green-300 dark:border-green-700 bg-green-100 dark:bg-green-900/30" :
                            status === "in_progress" ? "border-indigo-300 dark:border-indigo-700 bg-indigo-100 dark:bg-indigo-900/30" :
                            "border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800"}`}>
                          {status.replace("_", " ")}
                        </span>
                      </div>
                    </div>
                    {s.why_this && (
                      <p className="text-xs opacity-60 mt-1 leading-relaxed">{s.why_this}</p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {pathId && (
            <p className="text-gray-400 text-xs text-center pt-1">Click any step to advance its status</p>
          )}
        </div>
      )}

      {steps.length === 0 && !loading && (
        <div className="border border-dashed border-gray-200 dark:border-gray-700 rounded-xl p-6 text-center">
          <p className="text-gray-400 text-sm">No path loaded.</p>
          <p className="text-gray-500 text-xs mt-1">Type a role and hit Build, or click Load to view existing.</p>
        </div>
      )}
    </div>
  )
}