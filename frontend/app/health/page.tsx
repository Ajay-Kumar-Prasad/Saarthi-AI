"use client"

import { useEffect, useState } from "react"
import HealthStatCards from "@/components/health/HealthStatsCards"
import StepsCaloriesChart from "@/components/health/StepsCaloriesChart"
import ActivityLog from "@/components/health/ActivityLog"
import ActiveMinutesChart from "@/components/health/ActiveMinutesChart"
import HealthChatBox from "@/components/health/HealthChatBox"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { fetchHealthStatus } from "@/lib/api"
import { AgentResponse } from "@/types/agent"
import { HealthSummary } from "@/lib/health-api"

const USER_ID = "chjoshna145@gmail.com"

export default function HealthPage() {
  const [response, setResponse] = useState<AgentResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      const status = await fetchHealthStatus(USER_ID, 7)
      setResponse(status)
      setLoading(false)
    })()
  }, [])

  const status = (response?.data ?? { daily_metrics: [], activity_sessions: [] }) as HealthSummary

  return (
    <>
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

        {response && <AgentResponsePanel title="Health Agent" response={response} />}
        {status && <HealthStatCards data={status} />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {status && <StepsCaloriesChart metrics={status.daily_metrics ?? []} />}
            {status && <ActiveMinutesChart metrics={status.daily_metrics ?? []} />}
            {status && (status.activity_sessions ?? []).length > 0 && <ActivityLog sessions={status.activity_sessions ?? []} />}
            {status && (status.activity_sessions ?? []).length === 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">Recent Activities</p>
                <p className="text-gray-600 text-sm">No activity sessions in the last 7 days.</p>
              </div>
            )}
          </div>

          <div className="space-y-6">
            <HealthChatBox />
          </div>
        </div>
      </div>
    </>
  )
}
