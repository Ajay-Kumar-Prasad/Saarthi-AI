import type { ActivitySession } from "@/lib/health-api"
import { format, parseISO } from "date-fns"

const ACTIVITY_ICONS: Record<string, string> = {
  running: "🏃",
  cycling: "🚴",
  yoga: "🧘",
  walking: "🚶",
  swimming: "🏊",
  strength: "🏋️",
  workout: "💪",
  hiking: "🥾",
}

function getIcon(type: string) {
  const key = type.toLowerCase()
  return ACTIVITY_ICONS[key] ?? "⚡"
}

function formatDuration(mins: number) {
  if (mins < 60) return `${mins}m`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

export default function ActivityLog({ sessions }: { sessions: ActivitySession[] }) {
  const sorted = [...sessions].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 8)

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-gray-400 text-xs uppercase tracking-wide mb-4">Recent Activities</p>
      {sorted.length === 0 ? (
        <p className="text-gray-600 text-sm">No activity sessions recorded.</p>
      ) : (
        <ul className="space-y-2">
          {sorted.map((s, i) => (
            <li
              key={i}
              className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{getIcon(s.activity_type)}</span>
                <div>
                  <p className="text-white text-sm font-medium capitalize">{s.activity_type}</p>
                  <p className="text-gray-500 text-xs">
                    {format(parseISO(s.date), "MMM d")} · {formatDuration(s.duration_minutes)}
                  </p>
                </div>
              </div>
              <div className="text-right">
                {s.calories != null && (
                  <p className="text-emerald-400 text-sm font-medium">{s.calories} kcal</p>
                )}
                {s.avg_heart_rate != null && (
                  <p className="text-gray-500 text-xs">{s.avg_heart_rate} bpm avg</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
