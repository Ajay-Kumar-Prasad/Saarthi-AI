import type { Resource } from "@/lib/api"

const typeIcon: Record<string, string> = {
  book: "📖", course: "🎓", article: "📄", video: "🎬", podcast: "🎧",
}

export default function ResourceList({ resources }: { resources: Resource[] }) {
  if (!resources.length) return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center text-gray-500 text-sm">
      No resources in progress. Ask the chat to add one.
    </div>
  )
  return (
    <div className="flex flex-col gap-3">
      {resources.map((r) => (
        <div key={r.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{typeIcon[r.resource_type] ?? "📚"}</span>
              <div>
                <p className="text-white font-medium text-sm">{r.title}</p>
                {r.author && <p className="text-gray-500 text-xs mt-0.5">{r.author}</p>}
                <div className="flex gap-1 mt-1">
                  {r.tags.slice(0, 3).map((t) => (
                    <span key={t} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">{t}</span>
                  ))}
                </div>
              </div>
            </div>
            <span className="text-xs text-gray-400 shrink-0">{r.progress_pct}%</span>
          </div>
          <div className="mt-3 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all"
              style={{ width: `${r.progress_pct}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
