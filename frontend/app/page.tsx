import Header from "@/components/shared/Header"
import Link from "next/link"
import {
  BookOpen,
  Briefcase,
  Heart,
  DollarSign,
  Users
} from "lucide-react"

const agents = [
  {
    name: "Learning",
    href: "/learning",
    icon: BookOpen,
    desc: "Books, courses, flashcards, skill gaps, learning paths",
    owner: "Ajay Kumar Prasad",
    stats: ["Skill gap analysis", "SM-2 flashcards", "Learning paths", "Calendar sync"],
  },
  {
    name: "Work",
    href: "/work",
    icon: Briefcase,
    desc: "Tasks, meetings, emails, conflict detection",
    owner: "Hariharan S",
    stats: [],
  },
  {
    name: "Health",
    href: "/health",
    icon: Heart,
    desc: "Sleep, fitness, activity insights",
    owner: "Joshna Ch",
    stats: [],
  },
  {
    name: "Finance",
    href: "/finance",
    icon: DollarSign,
    desc: "Expense tracking, budget insights",
    owner: "Shubham Negi",
    stats: [],
  },
  {
    name: "Social",
    href: "/social",
    icon: Users,
    desc: "Events, relationships, reminders",
    owner: "Team",
    stats: [],
  },
]

export default function Dashboard() {
  return (
    <>
      <Header
        title="Dashboard"
        subtitle="Saarthi AI · GenAI Academy APAC Edition 2026 · Hack2skill × Google Cloud"
      />

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
          {agents.map((a) => {
            const Icon = a.icon;

            return (
              <Link
                key={a.name}
                href={a.href}
                className="group block rounded-xl p-5 transition-all bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 hover:border-indigo-400 dark:hover:border-indigo-500 hover:shadow-md cursor-pointer"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 text-indigo-500">
                    <Icon size={20} />
                  </span>

                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                    live
                  </span>
                </div>

                <h2 className="text-gray-900 dark:text-white font-bold text-lg">
                  {a.name}
                </h2>

                <p className="text-indigo-600 dark:text-indigo-400 text-xs mt-0.5">
                  AI-powered agent
                </p>

                <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                  {a.desc}
                </p>

                {a.stats.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {a.stats.map((s) => (
                      <span
                        key={s}
                        className="text-xs bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900 px-2 py-0.5 rounded-full"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}

                <p className="text-gray-400 text-xs mt-3 font-medium">
                  {a.owner}
                </p>
              </Link>
            );
          })}
        </div>
      </div>
    </>
  )
}