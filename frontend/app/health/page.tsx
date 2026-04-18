"use client"

import { useEffect, useState } from "react"
import HealthStatCards from "@/components/health/HealthStatsCards"
import StepsCaloriesChart from "@/components/health/StepsCaloriesChart"
import ActiveMinutesChart from "@/components/health/ActiveMinutesChart"
import HealthChatBox from "@/components/health/HealthChatBox"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { fetchHealthStatus } from "@/lib/api"
import { AgentResponse } from "@/types/agent"
import { ActivitySession } from "@/lib/health-api"

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

// ✅ Move OUTSIDE component
function mapToActivitySessions(data: Record<string, unknown>[]): ActivitySession[] {
  return data.map((s) => ({
    date: String(s.date ?? ""),
    activity_type: String(s.activity_type ?? "unknown"),
    start_time: String(s.start_time ?? ""),
    end_time: String(s.end_time ?? ""),
    duration_minutes: Number(s.duration_minutes ?? 0),
    calories_burned: s.calories_burned as number | null | undefined,
    steps: s.steps as number | null | undefined,
    distance_meters: s.distance_meters as number | null | undefined,
    avg_heart_rate: s.avg_heart_rate as number | null | undefined,
  }))
}

export default function HealthPage() {
  const [response, setResponse] = useState<AgentResponse<HealthStatusData> | null>(null)
  const [loading, setLoading] = useState(true)
  const [connectedUserId, setConnectedUserId] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [emailInput, setEmailInput] = useState("")

  useEffect(() => {
    void (async () => {
      try {
        const authStatusResponse = await fetch("/api/health/auth-status", {
          cache: "no-store",
        })
        const authStatus = (await authStatusResponse.json().catch(() => ({}))) as {
          connected?: boolean
          userId?: string | null
        }

        const cookieUserId =
          typeof authStatus.userId === "string" && authStatus.userId.trim()
            ? authStatus.userId.trim()
            : null

        setIsConnected(Boolean(authStatus.connected && cookieUserId))

        if (cookieUserId) {
          setConnectedUserId(cookieUserId)
          setEmailInput(cookieUserId)
        } else {
          setResponse(null)
          return
        }

        const res = await fetchHealthStatus(cookieUserId)
        setResponse(res)
      } catch (err) {
        console.error("Health fetch failed:", err)

        setResponse({
          agent: "health_agent",
          status: "error",
          summary: "Failed to fetch health data",
          conflicts: [],
          actions_taken: [],
          data: {
            daily_metrics: [],
            activity_sessions: [],
          },
        })
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const data = response?.data ?? {
    daily_metrics: [],
    activity_sessions: [],
  }

  const dailyMetrics = data.daily_metrics
  const sessions = data.activity_sessions

  // ✅ Precompute
  const activitySessions = mapToActivitySessions(sessions)
  const connectHref = emailInput.trim()
    ? `/api/health/connect?user_id=${encodeURIComponent(emailInput.trim())}`
    : null

  return (
    <div className="p-8 space-y-6">

      {loading && (
        <div className="bg-gray-100 border border-gray-200 text-gray-600 text-sm rounded-xl px-4 py-3 dark:bg-gray-900 dark:border-gray-800 dark:text-gray-400">
          Loading health dashboard...
        </div>
      )}

      {!loading && response && response.status === "error" && (
        <div className="bg-red-950 border border-red-800 text-red-400 text-sm rounded-xl px-4 py-3">
          {response.summary}
        </div>
      )}

      {!loading && !isConnected && (
        <div className="relative overflow-hidden rounded-3xl border border-amber-300/80 bg-[linear-gradient(135deg,rgba(251,191,36,0.2),rgba(255,251,235,0.95),rgba(253,230,138,0.35))] p-6 text-sm text-amber-950 shadow-[0_18px_60px_rgba(245,158,11,0.16)] dark:border-amber-700/60 dark:bg-[linear-gradient(135deg,rgba(120,53,15,0.95),rgba(41,37,36,0.96),rgba(120,53,15,0.88))] dark:text-amber-100">
          <div className="pointer-events-none absolute inset-y-0 right-0 w-40 bg-[radial-gradient(circle_at_top_right,rgba(251,191,36,0.35),transparent_65%)] dark:bg-[radial-gradient(circle_at_top_right,rgba(251,191,36,0.18),transparent_65%)]" />
          <div className="relative">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-amber-400/60 bg-white/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-700 dark:border-amber-600/50 dark:bg-black/20 dark:text-amber-300">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Health Access
            </div>
            <p className="text-lg font-semibold tracking-tight">Connect Google Fit to load your health dashboard.</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-amber-900/80 dark:text-amber-100/80">
              Enter the email you want to connect, then continue to Google consent.
            </p>
            <div className="mt-5 flex flex-col gap-3 lg:flex-row">
              <label className="group flex min-w-0 flex-1 items-center gap-3 rounded-2xl border border-amber-300/80 bg-white/90 px-4 py-3 shadow-sm transition-colors focus-within:border-amber-500 dark:border-amber-700/70 dark:bg-black/20">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300">
                  @
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700/70 dark:text-amber-300/70">
                    Google account email
                  </div>
                  <input
                    type="email"
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    placeholder="you@example.com"
                    className="mt-1 w-full border-0 bg-transparent p-0 text-sm text-gray-900 outline-none placeholder:text-amber-700/45 dark:text-white dark:placeholder:text-amber-200/35"
                  />
                </div>
              </label>
              <a
                href={connectHref ?? "#"}
                aria-disabled={!connectHref}
                className={`inline-flex min-h-14 items-center justify-center rounded-2xl px-5 text-sm font-semibold transition-all ${
                  connectHref
                    ? "bg-amber-500 text-black shadow-[0_12px_30px_rgba(245,158,11,0.28)] hover:-translate-y-0.5 hover:bg-amber-400"
                    : "pointer-events-none bg-amber-200 text-amber-700 dark:bg-amber-900 dark:text-amber-300"
                }`}
              >
                Connect Google Fit
              </a>
            </div>
          </div>
        </div>
      )}

      {response && (
        <AgentResponsePanel title="Health Agent" response={response} />
      )}

      {response && (
        <HealthStatCards
          data={{
            user_id: connectedUserId ?? "Not connected",
            period_days: dailyMetrics.length,
            sleep_sessions: [],
            activity_sessions: activitySessions,
            daily_metrics: dailyMetrics,
            avg_sleep_minutes: null,
            avg_steps: null,
            avg_resting_heart_rate: null,
            total_active_minutes: null,
          }}
        />
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        <div className="space-y-6 lg:col-span-2">
          <StepsCaloriesChart metrics={dailyMetrics} />
          <ActiveMinutesChart metrics={dailyMetrics} />

          {sessions.length > 0 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">
                Recent Activities
              </p>
              <p className="text-gray-300 text-sm">
                {sessions.length} activities recorded.
              </p>
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">
                Recent Activities
              </p>
              <p className="text-gray-600 text-sm">
                No activity sessions in the last 7 days.
              </p>
            </div>
          )}
        </div>

        {isConnected && (
          <div className="space-y-6">
            <HealthChatBox />
          </div>
        )}
      </div>
    </div>
  )
}
