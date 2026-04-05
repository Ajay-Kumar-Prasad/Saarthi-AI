"use client"
import { useState } from "react"
import { api } from "@/lib/api"

const ROLES = ["Data Engineer", "ML Engineer", "Cloud Engineer", "Backend Developer"]

export default function SkillGap() {
  const [role, setRole] = useState(ROLES[0])
  const [result, setResult] = useState<null | { summary: string; data: Record<string, unknown> }>(null)
  const [loading, setLoading] = useState(false)

  async function analyse() {
    setLoading(true)
    try {
      const res = await api.learning.skillGap(role)
      setResult(res)
    } finally {
      setLoading(false)
    }
  }

  const gap = result?.data as Record<string, unknown> | null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h3 className="text-white font-medium mb-4">Skill Gap Analysis</h3>
      <div className="flex gap-2 mb-4">
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2">
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </select>
        <button
          onClick={analyse}
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors">
          {loading ? "Analysing…" : "Analyse"}
        </button>
      </div>

      {gap && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-gray-400 text-sm">Readiness</span>
            <span className="text-white font-semibold">{String(gap.readiness_pct ?? 0)}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all"
              style={{ width: `${gap.readiness_pct ?? 0}%` }}
            />
          </div>
          {Array.isArray(gap.missing_required) && gap.missing_required.length > 0 && (
            <div>
              <p className="text-red-400 text-xs font-medium mb-1">Missing required</p>
              <div className="flex flex-wrap gap-1">
                {(gap.missing_required as string[]).map((s) => (
                  <span key={s} className="text-xs bg-red-950 text-red-400 border border-red-900 px-2 py-0.5 rounded-full">{s}</span>
                ))}
              </div>
            </div>
          )}
          {Array.isArray(gap.matched) && gap.matched.length > 0 && (
            <div>
              <p className="text-green-400 text-xs font-medium mb-1">You have</p>
              <div className="flex flex-wrap gap-1">
                {(gap.matched as string[]).map((s) => (
                  <span key={s} className="text-xs bg-green-950 text-green-400 border border-green-900 px-2 py-0.5 rounded-full">{s}</span>
                ))}
              </div>
            </div>
          )}
          <p className="text-gray-400 text-xs mt-2">{result?.summary}</p>
        </div>
      )}
    </div>
  )
}
