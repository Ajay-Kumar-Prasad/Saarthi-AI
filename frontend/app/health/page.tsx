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

const USER_ID = "chjoshna145@gmail.com"

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

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetchHealthStatus(USER_ID)
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

      {response && (
        <AgentResponsePanel title="Health Agent" response={response} />
      )}

      {response && (
        <HealthStatCards
          data={{
            user_id: USER_ID,
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <div className="lg:col-span-2 space-y-6">
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

        <div className="space-y-6">
          <HealthChatBox />
        </div>
      </div>
    </div>
  )
}