import type { Session } from "@/lib/api"

const typeIcon: Record<string, string> = {
  book: "📖", course: "🎓", article: "📄", video: "🎬", podcast: "🎧",
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString("en-IN", {
    weekday: "short", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

export default function UpcomingSessions({ sessions }: { sessions: Session[] }) {
  if (!sessions.length) return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center text-gray-500 text-sm">
      No upcoming sessions. Ask the chat to schedule one.
    </div>
  )
  return (
    <div className="flex flex-col gap-2">
      {sessions.map((s) => (
        <div key={s.id} className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 flex items-center gap-3">
          <span className="text-xl">{typeIcon[s.resource_type ?? ""] ?? "📚"}</span>
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate">{s.resource_title ?? s.title}</p>
            <p className="text-gray-500 text-xs">{formatDate(s.scheduled_at)} · {s.duration_minutes}min</p>
          </div>
          {s.calendar_event_id && (
            <span className="text-xs text-green-400 bg-green-950 border border-green-900 px-2 py-0.5 rounded-full shrink-0">
              synced
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
