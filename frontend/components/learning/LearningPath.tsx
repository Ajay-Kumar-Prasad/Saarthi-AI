"use client"
import { useState } from "react"
import { api } from "@/lib/api"

const STATUS_STYLE: Record<string, string> = {
  completed: "bg-green-900 border-green-700 text-green-400",
  in_progress: "bg-indigo-900 border-indigo-700 text-indigo-400",
  pending: "bg-gray-800 border-gray-700 text-gray-400",
  skipped: "bg-gray-800 border-gray-700 text-gray-600 line-through",
}

export default function LearningPath() {
  const [steps, setSteps] = useState<{ title: string; status: string; why_this: string; step_order: number }[]>([])
  const [loading, setLoading] = useState(false)
  const [role, setRole] = useState("")

  async function create() {
    if (!role.trim()) return
    setLoading(true)
    try {
      const res = await api.learning.path(`I want to become a ${role}, create a roadmap for me`)
      const raw = (res?.data as Record<string, unknown>)
      const pathData = raw?.learning_path as Record<string, unknown>
      const s = Array.isArray(pathData?.steps) ? pathData.steps as typeof steps : []
      setSteps(s)
    } finally {
      setLoading(false)
    }
  }

  async function loadExisting() {
    setLoading(true)
    try {
      const res = await api.learning.path("Show my learning path")
      const raw = (res?.data as Record<string, unknown>)
      const pathData = (raw?.path as Record<string, unknown>) ?? {}
      const s = Array.isArray(pathData?.steps) ? pathData.steps as typeof steps : []
      setSteps(s)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h3 className="text-white font-medium mb-4">Learning Path</h3>
      <div className="flex gap-2 mb-4">
        <input
          value={role}
          onChange={(e) => setRole(e.target.value)}
          placeholder="e.g. Data Engineer"
          className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
        />
        <button onClick={create} disabled={loading || !role.trim()}
          className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors">
          Build
        </button>
        <button onClick={loadExisting} disabled={loading}
          className="px-3 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-white text-sm rounded-lg transition-colors">
          Load
        </button>
      </div>

      {steps.length > 0 && (
        <div className="space-y-2">
          {steps.map((s, i) => (
            <div key={i} className={`border rounded-lg p-3 text-sm ${STATUS_STYLE[s.status] ?? STATUS_STYLE.pending}`}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs opacity-60">{s.step_order ?? i + 1}</span>
                <span className="font-medium">{s.title}</span>
                <span className="ml-auto text-xs opacity-70 capitalize">{s.status}</span>
              </div>
              {s.why_this && <p className="text-xs opacity-60 mt-1 ml-5">{s.why_this}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
