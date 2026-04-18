"use client"

import toast from "react-hot-toast"

type TimelineItem = {
  label: string
  intensity: number
}

type ConflictCardProps = {
  conflictId: string
  explanation?: string
  timeline?: TimelineItem[]
  onResolve?: (conflictId: string) => Promise<void> | void
  onReschedule?: (conflictId: string) => Promise<void> | void
}

const DEFAULT_TIMELINE: TimelineItem[] = [
  { label: "Now", intensity: 80 },
  { label: "+2h", intensity: 55 },
  { label: "+4h", intensity: 30 },
]

export default function ConflictCard({
  conflictId,
  explanation = "Your planned study session overlaps with a high-priority work deadline and low sleep recovery window.",
  timeline = DEFAULT_TIMELINE,
  onResolve,
  onReschedule,
}: ConflictCardProps) {
  async function resolveConflict() {
    try {
      if (onResolve) await onResolve(conflictId)
      toast.success("Conflict resolved successfully")
    } catch {
      toast.error("Could not resolve conflict")
    }
  }

  async function rescheduleConflict() {
    try {
      if (onReschedule) await onReschedule(conflictId)
      toast.success("Conflict rescheduled successfully")
    } catch {
      toast.error("Could not reschedule conflict")
    }
  }

  return (
    <div className="rounded-xl border border-red-300 bg-red-50/50 p-4 dark:border-red-800 dark:bg-red-950/20">
      <h3 className="text-sm font-semibold text-red-700 dark:text-red-300">Conflict Detected</h3>
      <p className="mt-2 text-sm leading-relaxed text-red-700/90 dark:text-red-200/90">{explanation}</p>

      <div className="mt-4 space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-red-600/80 dark:text-red-300/80">Timeline</p>
        <div className="space-y-2">
          {timeline.map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <span className="w-10 shrink-0 text-xs text-red-700/80 dark:text-red-200/80">{item.label}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-red-100 dark:bg-red-900/40">
                <div
                  className="h-full rounded-full bg-red-500 dark:bg-red-400"
                  style={{ width: `${Math.max(5, Math.min(100, item.intensity))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={resolveConflict}
          className="rounded-lg bg-red-600 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-red-500"
        >
          Resolve Conflict
        </button>
        <button
          type="button"
          onClick={rescheduleConflict}
          className="rounded-lg border border-red-300 bg-white px-3 py-2 text-xs font-medium text-red-700 transition-colors hover:bg-red-100 dark:border-red-800 dark:bg-red-950/30 dark:text-red-200 dark:hover:bg-red-900/40"
        >
          Reschedule
        </button>
      </div>
    </div>
  )
}

export type { ConflictCardProps, TimelineItem }
