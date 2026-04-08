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
    try { setResult(await api.learning.skillGap(role)) }
    finally { setLoading(false) }
  }

  const gap = result?.data as Record<string, unknown> | null
  const readiness = Number(gap?.readiness_pct ?? 0)

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <h3 className="text-gray-900 dark:text-white font-semibold mb-4">Skill Gap Analysis</h3>
      <div className="flex gap-2 mb-4">
        <select value={role} onChange={(e) => setRole(e.target.value)}
          className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500">
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </select>
        <button onClick={analyse} disabled={loading}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors font-medium">
          {loading ? "Analysing…" : "Analyse"}
        </button>
      </div>

      {gap && (
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-gray-500 dark:text-gray-400 text-sm">Readiness for {role}</span>
              <span className={`font-bold text-lg ${readiness >= 70 ? "text-green-600 dark:text-green-400" : readiness >= 40 ? "text-yellow-600 dark:text-yellow-400" : "text-red-600 dark:text-red-400"}`}>
                {readiness}%
              </span>
            </div>
            <div className="h-2.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${readiness}%`,
                  background: readiness >= 70 ? "#22c55e" : readiness >= 40 ? "#eab308" : "#ef4444"
                }} />
            </div>
          </div>

          {Array.isArray(gap.missing_required) && gap.missing_required.length > 0 && (
            <div>
              <p className="text-red-500 dark:text-red-400 text-xs font-semibold uppercase tracking-wide mb-2">
                Missing required ({(gap.missing_required as string[]).length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(gap.missing_required as string[]).map((s) => (
                  <span key={s} className="text-xs bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900 px-2.5 py-1 rounded-full">{s}</span>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(gap.missing_recommended) && gap.missing_recommended.length > 0 && (
            <div>
              <p className="text-yellow-600 dark:text-yellow-400 text-xs font-semibold uppercase tracking-wide mb-2">
                Recommended ({(gap.missing_recommended as string[]).length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(gap.missing_recommended as string[]).map((s) => (
                  <span key={s} className="text-xs bg-yellow-50 dark:bg-yellow-950 text-yellow-600 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-900 px-2.5 py-1 rounded-full">{s}</span>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(gap.skills_you_have) && (gap.skills_you_have as string[]).length > 0 && (
            <div>
              <p className="text-green-600 dark:text-green-400 text-xs font-semibold uppercase tracking-wide mb-2">
                You already have ({(gap.skills_you_have as string[]).length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(gap.skills_you_have as string[]).map((s) => (
                  <span key={s} className="text-xs bg-green-50 dark:bg-green-950 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-900 px-2.5 py-1 rounded-full">{s}</span>
                ))}
              </div>
            </div>
          )}

          {result?.summary && (
            <p className="text-gray-500 dark:text-gray-400 text-xs border-t border-gray-100 dark:border-gray-800 pt-3">{result.summary}</p>
          )}
        </div>
      )}
    </div>
  )
}
