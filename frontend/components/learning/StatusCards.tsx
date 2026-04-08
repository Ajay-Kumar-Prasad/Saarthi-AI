import type { LearningStatus } from "@/lib/api"

export default function StatusCards({ data }: { data: LearningStatus }) {
  const cards = [
    {
      label: "Study streak",
      value: `${data.streak_days}`,
      unit: data.streak_days === 1 ? "day" : "days",
      sub: data.streak_days > 0 ? "Keep it going!" : "Start today",
      color: "text-orange-500 dark:text-orange-400",
      bg: "bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-900/50",
    },
    {
      label: "This week",
      value: `${data.weekly_hours_studied}`,
      unit: "hours",
      sub: "studied so far",
      color: "text-green-600 dark:text-green-400",
      bg: "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900/50",
    },
    {
      label: "In progress",
      value: `${data.resources.length}`,
      unit: data.resources.length === 1 ? "resource" : "resources",
      sub: "actively learning",
      color: "text-blue-600 dark:text-blue-400",
      bg: "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-900/50",
    },
    {
      label: "Sessions ahead",
      value: `${data.upcoming_sessions.length}`,
      unit: "upcoming",
      sub: "next 7 days",
      color: "text-purple-600 dark:text-purple-400",
      bg: "bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-900/50",
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className={`border rounded-xl p-5 ${c.bg}`}>
          <p className="text-gray-500 dark:text-gray-500 text-xs mb-2 font-medium uppercase tracking-wide">{c.label}</p>
          <div className="flex items-baseline gap-1.5">
            <span className={`font-bold text-3xl ${c.color}`}>{c.value}</span>
            <span className="text-gray-500 dark:text-gray-500 text-sm">{c.unit}</span>
          </div>
          <p className="text-gray-400 dark:text-gray-600 text-xs mt-1">{c.sub}</p>
        </div>
      ))}
    </div>
  )
}
