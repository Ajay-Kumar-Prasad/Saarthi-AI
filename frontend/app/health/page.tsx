import Header from "@/components/shared/Header"
import HealthStatCards from "@/components/health/HealthStatsCards"
import StepsCaloriesChart from "@/components/health/StepsCaloriesChart"
import ActivityLog from "@/components/health/ActivityLog"
import ActiveMinutesChart from "@/components/health/ActiveMinutesChart"
import HealthChatBox from "@/components/health/HealthChatBox"
import type { HealthSummary } from "@/lib/health-api"

async function getHealthStatus(): Promise<HealthSummary | null> {
  try {
    const res = await fetch("http://localhost:8000/health/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "chjoshna145@gmail.com",
        days: 7,
      }),
      cache: "no-store",
    })
    if (!res.ok) return null
    const data = await res.json()
    return data
  } catch {
    return null
  }
}

export default async function HealthPage() {
  const status = await getHealthStatus()
  console.log("Health status:", status) // Log the fetched health status for debugging

  return (
    <>
      <div className="p-8 space-y-6">

        {!status && (
          <div className="bg-red-950 border border-red-800 text-red-400 text-sm rounded-xl px-4 py-3">
            Could not reach Health Agent on port 8000. 
          </div>
        )}

        {/* Stat Cards */}
        {status && <HealthStatCards data={status} />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left / main column */}
          <div className="lg:col-span-2 space-y-6">
            {status && (
              <StepsCaloriesChart metrics={status.daily_metrics} />
            )}
            {status && (
              <ActiveMinutesChart metrics={status.daily_metrics} />
            )}
            {status && status.activity_sessions.length > 0 && (
              <ActivityLog sessions={status.activity_sessions} />
            )}
            {status && status.activity_sessions.length === 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">Recent Activities</p>
                <p className="text-gray-600 text-sm">No activity sessions in the last 7 days.</p>
              </div>
            )}
          </div>

          {/* Right column */}
          <div className="space-y-6">
            <HealthChatBox />
          </div>
        </div>
      </div>
    </>
  )
}
