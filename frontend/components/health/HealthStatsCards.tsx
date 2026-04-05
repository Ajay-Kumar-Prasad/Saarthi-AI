import type { HealthSummary } from "@/lib/health-api"

function StatCard({
  label,
  value,
  unit,
  icon,
  sub,
}: {
  label: string
  value: string | number | null
  unit?: string
  icon: string
  sub?: string
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-gray-400 text-xs uppercase tracking-wide">{label}</p>
        <span className="text-lg">{icon}</span>
      </div>
      <p className="text-white text-2xl font-semibold">
        {value !== null && value !== undefined ? (
          <>
            {typeof value === "number" ? value.toLocaleString() : value}
            {unit && <span className="text-gray-500 text-sm font-normal ml-1">{unit}</span>}
          </>
        ) : (
          <span className="text-gray-600 text-base">No data</span>
        )}
      </p>
      {sub && <p className="text-gray-500 text-xs mt-1">{sub}</p>}
    </div>
  )
}

export default function HealthStatCards({ data }: { data: HealthSummary }) {
  const metrics = data.daily_metrics ?? []

  const stepsValues = metrics.map((d) => d.total_steps).filter((v): v is number => v != null)
  const caloriesValues = metrics.map((d) => d.total_calories).filter((v): v is number => v != null)
  const activeValues = metrics.map((d) => d.active_minutes).filter((v): v is number => v != null)

  const avgSteps =
    stepsValues.length > 0 ? Math.round(stepsValues.reduce((a, b) => a + b, 0) / stepsValues.length) : null
  const avgCalories =
    caloriesValues.length > 0 ? Math.round(caloriesValues.reduce((a, b) => a + b, 0) / caloriesValues.length) : null
  const totalActiveMinutes =
    activeValues.length > 0 ? activeValues.reduce((a, b) => a + b, 0) : null

  const stepsGoalPct =
    avgSteps != null ? Math.min(Math.round((avgSteps / 10000) * 100), 100) : null

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <StatCard
        label="Avg Daily Steps"
        icon="👟"
        value={avgSteps}
        sub={stepsGoalPct != null ? `${stepsGoalPct}% of 10,000 goal` : undefined}
      />
      <StatCard
        label="Avg Calories Burned"
        icon="🔥"
        value={avgCalories}
        unit="kcal/day"
        sub={caloriesValues.length > 0 ? `based on ${caloriesValues.length} days` : undefined}
      />
      <StatCard
        label="Total Active Minutes"
        icon="⚡"
        value={totalActiveMinutes}
        unit="min"
        sub={activeValues.length > 0 ? `across ${activeValues.length} days` : undefined}
      />
    </div>
  )
}
