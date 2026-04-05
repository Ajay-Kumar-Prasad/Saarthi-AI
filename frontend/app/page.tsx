import Header from "@/components/shared/Header"
import Link from "next/link"

const agents = [
  { name: "Learning", href: "/learning", icon: "📚", desc: "Books, courses, flashcards, skill gaps, learning paths", owner: "Ajay Kumar Prasad", live: true,
    stats: ["Skill gap analysis", "SM-2 flashcards", "Learning paths", "Calendar sync"] },
  { name: "Work", href: "/work", icon: "💼", desc: "Tasks, calendar, deadlines, conflict detection", owner: "Hariharan S", live: false, stats: [] },
  { name: "Health", href: "/health", icon: "❤️", desc: "Sleep, fitness, nutrition tracking", owner: "Joshna Ch", live: false, stats: [] },
  { name: "Finance", href: "/finance", icon: "💰", desc: "Budget, bills, spending analysis", owner: "Shubham Negi", live: false, stats: [] },
  { name: "Social", href: "/social", icon: "👥", desc: "Events, birthdays, relationships", owner: "Team", live: false, stats: [] },
]

export default function Dashboard() {
  return (
    <>
      <Header title="Dashboard" subtitle="Saarthi AI · GenAI Academy APAC Edition 2026 · Hack2skill × Google Cloud" />
      <div className="p-8">
        <div className="mb-8 bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 rounded-xl p-5">
          <p className="text-indigo-700 dark:text-indigo-300 font-semibold text-sm mb-1">
            सारथी — Your Personal Guide Through the Chaos of Modern Life
          </p>
          <p className="text-indigo-600 dark:text-indigo-400 text-xs leading-relaxed">
            Five AI agents sharing one memory, firing in parallel, catching conflicts you'd never notice alone.
            Built on Google ADK · AlloyDB AI · MCP · Cloud Run.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((a) => (
            <div key={a.name} className={`border rounded-xl p-5 transition-all
              ${a.live
                ? "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:border-indigo-400 dark:hover:border-indigo-500 hover:shadow-sm cursor-pointer"
                : "bg-gray-50 dark:bg-gray-900/50 border-gray-100 dark:border-gray-800 opacity-60"}`}>
              {a.live ? (
                <Link href={a.href} className="block">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-3xl">{a.icon}</span>
                    <span className="text-xs bg-green-50 dark:bg-green-950 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800 px-2 py-0.5 rounded-full font-medium">live</span>
                  </div>
                  <h2 className="text-gray-900 dark:text-white font-bold text-lg">{a.name}</h2>
                  <p className="text-gray-500 text-xs mt-1 leading-relaxed">{a.desc}</p>
                  {a.stats.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {a.stats.map((s) => (
                        <span key={s} className="text-xs bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900 px-2 py-0.5 rounded-full">{s}</span>
                      ))}
                    </div>
                  )}
                  <p className="text-gray-400 text-xs mt-3 font-medium">{a.owner}</p>
                </Link>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-3xl">{a.icon}</span>
                    <span className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full">soon</span>
                  </div>
                  <h2 className="text-gray-900 dark:text-white font-bold text-lg">{a.name}</h2>
                  <p className="text-gray-500 text-xs mt-1 leading-relaxed">{a.desc}</p>
                  <p className="text-gray-400 text-xs mt-3 font-medium">{a.owner}</p>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}