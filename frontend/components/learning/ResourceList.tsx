import type { Resource } from "@/lib/api"
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

const statusColor: Record<string, string> = {
  in_progress:
    "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-900",
  completed:
    "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-900",
  paused:
    "text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-900",
  not_started:
    "text-gray-500 bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700",
}

export default function ResourceList({ resources }: { resources: Resource[] }) {
  if (!resources.length) {
    return (
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 text-center text-gray-400 text-sm">
        No resources in progress. Ask the chat to add one.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {resources.map((r) => {
        const Icon = typeIcon[r.resource_type] ?? BookOpen

        return (
          <div
            key={r.id}
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors"
          >
            <div className="flex items-start gap-3">
              <span className="text-indigo-500 mt-0.5">
                <Icon size={20} />
              </span>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-gray-900 dark:text-white font-semibold text-sm truncate">
                    {r.title}
                  </p>
                  <span className="text-sm font-bold text-indigo-600 dark:text-indigo-400 shrink-0">
                    {r.progress_pct}%
                  </span>
                </div>

                {r.author && (
                  <p className="text-gray-500 text-xs mt-0.5">
                    {r.author}
                  </p>
                )}

                <div className="flex items-center gap-2 mt-2">
                  <span
                    className={`text-xs border px-2 py-0.5 rounded-full capitalize ${
                      statusColor[r.status] ?? statusColor.not_started
                    }`}
                  >
                    {r.status.replace("_", " ")}
                  </span>

                  {r.tags.slice(0, 3).map((t) => (
                    <span
                      key={t}
                      className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 px-2 py-0.5 rounded-full"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-3 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${r.progress_pct}%`,
                  background:
                    r.progress_pct === 100
                      ? "#22c55e"
                      : r.progress_pct > 50
                      ? "#6366f1"
                      : "#818cf8",
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}