import type { Session } from "@/lib/api"
import {
  BookOpen,
  GraduationCap,
  FileText,
  Video,
  Podcast,
} from "lucide-react"

const typeIcon: Record<string, React.ElementType> = {
  book: BookOpen,
  course: GraduationCap,
  article: FileText,
  video: Video,
  podcast: Podcast,
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString("en-IN", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function UpcomingSessions({ sessions }: { sessions: Session[] }) {
  if (!sessions.length) return null

  return (
    <div className="flex flex-col gap-2">
      {sessions.map((s) => {
        const Icon = typeIcon[s.resource_type ?? ""] ?? BookOpen

        return (
          <div
            key={s.id}
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-3 flex items-center gap-3 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors"
          >
            <span className="text-indigo-500">
              <Icon size={18} />
            </span>

            <div className="flex-1 min-w-0">
              <p className="text-gray-900 dark:text-white text-sm font-medium truncate">
                {s.resource_title ?? s.title}
              </p>
              <p className="text-gray-500 text-xs mt-0.5">
                {formatDate(s.scheduled_at)} · {s.duration_minutes}min
              </p>
            </div>

            {s.calendar_event_id ? (
              <span className="text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-900 px-2 py-0.5 rounded-full shrink-0">
                synced
              </span>
            ) : (
              <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-2 py-0.5 rounded-full shrink-0">
                local
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}