import type { HealthSummary } from "@/lib/health-api"
import { Flame, Footprints, Zap, type LucideIcon } from "lucide-react"

const STEP_GOAL = 10000

function extractNumbers<T>(
  arr: T[],
  selector: (item: T) => number | null | undefined
): number[] {
  return arr.map(selector).filter((v): v is number => v != null && v >= 0)
}

function sum(arr: number[]) {
  return arr.reduce((a, b) => a + b, 0)
}

function StatCard({
  label,
  value,
  unit,
  Icon,
  sub,
}: {
  label: string
  value: string | number | null
  unit?: string
  Icon: LucideIcon
  sub?: string
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
        <Icon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
      </div>
      <p className="text-2xl font-semibold text-gray-900 dark:text-white">
        {value !== null && value !== undefined ? (
          <>
            {typeof value === "number" ? value.toLocaleString() : value}
            {unit && <span className="ml-1 text-sm font-normal text-gray-500 dark:text-gray-500">{unit}</span>}
          </>
        ) : (
          <span className="text-base text-gray-500 dark:text-gray-400">No data</span>
        )}
      </p>
      {sub && <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">{sub}</p>}
    </div>
  )
}

export default function HealthStatCards({ data }: { data: HealthSummary }) {
  const metrics = Array.isArray(data.daily_metrics) ? data.daily_metrics : []

  const stepsValues = extractNumbers(metrics, (d) => d.total_steps)
  const caloriesValues = extractNumbers(metrics, (d) => d.total_calories)
  const activeValues = extractNumbers(metrics, (d) => d.active_minutes)

  const avgSteps =
    stepsValues.length > 0 ? Math.round(sum(stepsValues) / stepsValues.length) : null

  const avgCalories =
    caloriesValues.length > 0 ? Math.round(sum(caloriesValues) / caloriesValues.length) : null

  const totalActiveMinutes =
    activeValues.length > 0 ? sum(activeValues) : null

  const stepsGoalPct =
    avgSteps != null ? Math.min(Math.round((avgSteps / STEP_GOAL) * 100), 100) : null

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <StatCard
        label="Avg Daily Steps"
        Icon={Footprints}
        value={avgSteps}
        sub={stepsGoalPct != null ? `${stepsGoalPct}% of ${STEP_GOAL.toLocaleString()} goal` : undefined}
      />
      <StatCard
        label="Avg Calories Burned"
        Icon={Flame}
        value={avgCalories}
        unit="kcal/day"
        sub={caloriesValues.length > 0 ? `based on ${caloriesValues.length} days` : undefined}
      />
      <StatCard
        label="Total Active Minutes"
        Icon={Zap}
        value={totalActiveMinutes}
        unit="min"
        sub={activeValues.length > 0 ? `across ${activeValues.length} days` : undefined}
      />
    </div>
  )
}
