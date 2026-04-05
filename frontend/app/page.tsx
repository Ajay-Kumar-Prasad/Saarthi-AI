import Header from "@/components/shared/Header"
import Link from "next/link"

const agents = [
  { name: "Learning", href: "/learning", icon: "📚", desc: "Books, courses, flashcards, skill gaps", owner: "Ajay Kumar", live: true },
  { name: "Work", href: "/work", icon: "💼", desc: "Tasks, calendar, deadlines", owner: "Hariharan S", live: false },
  { name: "Health", href: "/health", icon: "❤️", desc: "Sleep, fitness, nutrition", owner: "Joshna Ch", live: true },
  { name: "Finance", href: "/finance", icon: "💰", desc: "Budget, bills, spending", owner: "Shubham Negi", live: false },
  { name: "Social", href: "/social", icon: "👥", desc: "Events, birthdays, relationships", owner: "Team", live: false },
]

export default function Dashboard() {
  return (
    <>
      <Header title="Dashboard" subtitle="Saarthi AI · GenAI Academy APAC 2026" />
      <div className="p-8">
        <p className="text-gray-400 text-sm mb-6">Five agents. One memory. Zero context-switching.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((a) => (
            <div
              key={a.name}
              className={`bg-gray-900 border rounded-xl p-5 transition-all
                ${a.live ? "border-gray-700 hover:border-indigo-500 cursor-pointer" : "border-gray-800 opacity-50"}`}
            >
              {a.live ? (
                <Link href={a.href} className="block">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-3xl">{a.icon}</span>
                    <span className="text-xs bg-green-900 text-green-400 border border-green-800 px-2 py-0.5 rounded-full">live</span>
                  </div>
                  <h2 className="text-white font-semibold">{a.name}</h2>
                  <p className="text-gray-500 text-xs mt-1">{a.desc}</p>
                  <p className="text-gray-600 text-xs mt-3">{a.owner}</p>
                </Link>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-3xl">{a.icon}</span>
                    <span className="text-xs bg-gray-800 text-gray-600 px-2 py-0.5 rounded-full">soon</span>
                  </div>
                  <h2 className="text-white font-semibold">{a.name}</h2>
                  <p className="text-gray-500 text-xs mt-1">{a.desc}</p>
                  <p className="text-gray-600 text-xs mt-3">{a.owner}</p>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
