import type { HealthSummary } from "@/lib/health-api"
import {
  Footprints,
  Flame,
  Zap,
} from "lucide-react"

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
  icon,
  sub,
}: {
  label: string
  value: string | number | null
  unit?: string
  icon: React.ElementType
  sub?: string
}) {
  const Icon = icon

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-gray-400 text-xs uppercase tracking-wide">
          {label}
        </p>

        <span className="text-indigo-500">
          <Icon size={18} />
        </span>
      </div>

      <p className="text-white text-2xl font-semibold">
        {value !== null && value !== undefined ? (
          <>
            {typeof value === "number"
              ? value.toLocaleString()
              : value}
            {unit && (
              <span className="text-gray-500 text-sm font-normal ml-1">
                {unit}
              </span>
            )}
          </>
        ) : (
          <span className="text-gray-600 text-base">
            No data
          </span>
        )}
      </p>

      {sub && (
        <p className="text-gray-500 text-xs mt-1">
          {sub}
        </p>
      )}
    </div>
  )
}

export default function HealthStatCards({ data }: { data: HealthSummary }) {
  const metrics = Array.isArray(data.daily_metrics) ? data.daily_metrics : []

  const stepsValues = extractNumbers(metrics, (d) => d.total_steps)
  const caloriesValues = extractNumbers(metrics, (d) => d.total_calories)
  const activeValues = extractNumbers(metrics, (d) => d.active_minutes)

  const avgSteps =
    stepsValues.length > 0
      ? Math.round(sum(stepsValues) / stepsValues.length)
      : null

  const avgCalories =
    caloriesValues.length > 0
      ? Math.round(sum(caloriesValues) / caloriesValues.length)
      : null

  const totalActiveMinutes =
    activeValues.length > 0 ? sum(activeValues) : null

  const stepsGoalPct =
    avgSteps != null
      ? Math.min(Math.round((avgSteps / STEP_GOAL) * 100), 100)
      : null

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <StatCard
        label="Avg Daily Steps"
        icon={Footprints}
        value={avgSteps}
        sub={
          stepsGoalPct != null
            ? `${stepsGoalPct}% of ${STEP_GOAL.toLocaleString()} goal`
            : undefined
        }
      />

      <StatCard
        label="Avg Calories Burned"
        icon={Flame}
        value={avgCalories}
        unit="kcal/day"
        sub={
          caloriesValues.length > 0
            ? `based on ${caloriesValues.length} days`
            : undefined
        }
      />

      <StatCard
        label="Total Active Minutes"
        icon={Zap}
        value={totalActiveMinutes}
        unit="min"
        sub={
          activeValues.length > 0
            ? `across ${activeValues.length} days`
            : undefined
        }
      />
    </div>
  )
}