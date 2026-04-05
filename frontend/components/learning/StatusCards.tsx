import type { LearningStatus } from "@/lib/api"

export default function StatusCards({ data }: { data: LearningStatus }) {
  const cards = [
    { label: "Streak", value: `${data.streak_days} days`, color: "text-orange-400" },
    { label: "This week", value: `${data.weekly_hours_studied}h studied`, color: "text-green-400" },
    { label: "In progress", value: `${data.resources.length} resources`, color: "text-blue-400" },
    { label: "Goals", value: `${data.active_goals.length} active`, color: "text-purple-400" },
  ]
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-gray-500 text-xs mb-1">{c.label}</p>
          <p className={`font-semibold text-lg ${c.color}`}>{c.value}</p>
        </div>
      ))}
    </div>
  )
}
