import type { LearningStatus } from "@/lib/api"

export default function StatusCards({ data }: { data: LearningStatus }) {
  const cards = [
    {
      label: "Study streak",
      value: `${data.streak_days} day${data.streak_days !== 1 ? "s" : ""}`,
      sub: data.streak_days > 0 ? "Keep it up!" : "Start today",
      color: "text-orange-400",
      bg: "bg-orange-950/30 border-orange-900/50",
    },
    {
      label: "This week",
      value: `${data.weekly_hours_studied}h`,
      sub: "hours studied",
      color: "text-green-400",
      bg: "bg-green-950/30 border-green-900/50",
    },
    {
      label: "In progress",
      value: `${data.resources.length}`,
      sub: data.resources.length === 1 ? "resource" : "resources",
      color: "text-blue-400",
      bg: "bg-blue-950/30 border-blue-900/50",
    },
    {
      label: "Upcoming sessions",
      value: `${data.upcoming_sessions.length}`,
      sub: "next 7 days",
      color: "text-purple-400",
      bg: "bg-purple-950/30 border-purple-900/50",
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className={`border rounded-xl p-4 ${c.bg}`}>
          <p className="text-gray-500 text-xs mb-1">{c.label}</p>
          <p className={`font-bold text-2xl ${c.color}`}>{c.value}</p>
          <p className="text-gray-600 text-xs mt-0.5">{c.sub}</p>
        </div>
      ))}
    </div>
  )
}
