"use client"
import { useState, useEffect } from "react"
import { api, fetchLearningStatus, Goal } from "@/lib/api"

const USER_ID = "chjoshna145@gmail.com"

async function createGoalOnBackend(data: {
  title: string
  weekly_hours_target: number
  target_date?: string
}) {
  return api.learning.chat(
    `Create a study goal: title="${data.title}", weekly target=${data.weekly_hours_target} hours${data.target_date ? `, target date=${data.target_date}` : ""}`,
  )
}

async function fetchGoals(): Promise<Goal[]> {
  const response = await fetchLearningStatus(USER_ID)
  return response.data?.active_goals ?? []
}

const STATUS_STYLES: Record<string, string> = {
  active:    "bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800",
  completed: "bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-400 border-indigo-200 dark:border-indigo-800",
  paused:    "bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800",
}

function GoalCard({ goal }: { goal: Goal }) {
  const pct = Math.min(100, Math.round(goal.progress_pct ?? 0))
  const statusStyle = STATUS_STYLES[goal.status] ?? STATUS_STYLES.active

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <p className="text-gray-900 dark:text-white font-semibold text-sm truncate">{goal.title}</p>
          {goal.target_date && (
            <p className="text-gray-400 text-xs mt-0.5">
              Due {new Date(goal.target_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
            </p>
          )}
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 ${statusStyle}`}>
          {goal.status}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-1.5">
          <div
            className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-indigo-500 dark:text-indigo-400 font-semibold text-sm shrink-0">{pct}%</span>
      </div>

      <p className="text-gray-400 text-xs mt-2">
        Target: <span className="text-gray-600 dark:text-gray-300 font-medium">
          {Number(goal.weekly_hours_target)}h / week
        </span>
      </p>
    </div>
  )
}

export default function StudyGoals({ initialGoals }: { initialGoals: Goal[] }) {
  const [goals, setGoals] = useState<Goal[]>(initialGoals)
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState("")
  const [hours, setHours] = useState("")
  const [targetDate, setTargetDate] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Sync when parent re-fetches status
  useEffect(() => {
    setGoals(initialGoals)
  }, [initialGoals])

  async function handleCreate() {
    if (!title.trim() || !hours) return
    const hoursNum = parseFloat(hours)
    if (isNaN(hoursNum) || hoursNum <= 0) {
      setError("Weekly hours must be a positive number.")
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const res = await createGoalOnBackend({
        title: title.trim(),
        weekly_hours_target: hoursNum,
        target_date: targetDate || undefined,
      })

      setSuccess(res?.summary ?? "Goal created!")
      setTitle("")
      setHours("")
      setTargetDate("")
      setShowForm(false)

      const fresh = await fetchGoals()
      if (fresh.length > 0) {
        setGoals(fresh)
      } else {
        const optimistic: Goal = {
          id: crypto.randomUUID(),
          title: title.trim(),
          weekly_hours_target: hoursNum,
          progress_pct: 0,
          target_date: targetDate || null,
          status: "active",
        }
        setGoals((prev) => [optimistic, ...prev])
      }

      setTimeout(() => setSuccess(null), 3000)
    } catch {
      setError("Failed to create goal. Is the backend running?")
    } finally {
      setLoading(false)
    }
  }

  const active    = goals.filter((g) => g.status === "active")
  const completed = goals.filter((g) => g.status === "completed")

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-gray-400 text-xs uppercase tracking-wide">Study Goals</p>
        <button
          onClick={() => { setShowForm((v) => !v); setError(null); setSuccess(null) }}
          className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded-lg transition-colors font-medium"
        >
          {showForm ? "Cancel" : "+ New Goal"}
        </button>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-gray-900 border border-indigo-200 dark:border-indigo-800 rounded-xl p-4 mb-4 space-y-3">
          <p className="text-gray-900 dark:text-white text-sm font-semibold">New Study Goal</p>
          <div>
            <label className="text-gray-500 text-xs mb-1 block">Goal title *</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Complete Python Crash Course"
              className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-gray-500 text-xs mb-1 block">Weekly hours target *</label>
              <input
                type="number"
                min="0.5"
                step="0.5"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                placeholder="e.g. 5"
                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
            <div>
              <label className="text-gray-500 text-xs mb-1 block">Target date (optional)</label>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
          </div>
          {error && <p className="text-red-400 text-xs">{error}</p>}
          {success && <p className="text-green-400 text-xs">{success}</p>}
          <button
            onClick={handleCreate}
            disabled={loading || !title.trim() || !hours}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium py-2 rounded-lg transition-colors"
          >
            {loading ? "Creating…" : "Create Goal"}
          </button>
        </div>
      )}

      {success && !showForm && (
        <p className="text-green-400 text-xs mb-3">{success}</p>
      )}

      {active.length > 0 && (
        <div className="space-y-3 mb-4">
          {active.map((g) => <GoalCard key={g.id} goal={g} />)}
        </div>
      )}

      {completed.length > 0 && (
        <div>
          <p className="text-gray-500 text-xs uppercase tracking-wide mb-2 mt-4">Completed</p>
          <div className="space-y-3">
            {completed.map((g) => <GoalCard key={g.id} goal={g} />)}
          </div>
        </div>
      )}

      {goals.length === 0 && !showForm && (
        <div className="bg-white dark:bg-gray-900 border border-dashed border-gray-200 dark:border-gray-700 rounded-xl p-6 text-center">
          <p className="text-gray-400 text-sm">No study goals yet.</p>
          <p className="text-gray-500 text-xs mt-1">Set a weekly target to stay on track.</p>
        </div>
      )}
    </div>
  )
}