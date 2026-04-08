"use client"

import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"

type MorningBriefingResponse = {
  name?: string
  chaos_score?: number
  recommendations?: string[]
}

const DEFAULT_RECOMMENDATIONS = [
  "Start with your top-priority work block before checking notifications.",
  "Move low-impact meetings to late afternoon to preserve focus hours.",
  "Schedule a 20-minute recovery break after your heaviest task.",
]

export default function MorningBriefing() {
  const [briefing, setBriefing] = useState<MorningBriefingResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const seen = sessionStorage.getItem("morning-briefing-seen")
    if (!seen) {
      setIsVisible(true)
      sessionStorage.setItem("morning-briefing-seen", "true")
    }
  }, [])

  useEffect(() => {
    if (!isVisible) {
      setIsLoading(false)
      return
    }

    async function loadBriefing() {
      try {
        const res = await fetch("/api/morning-briefing", { method: "GET" })
        if (!res.ok) throw new Error("Failed to fetch morning briefing")
        const data = (await res.json()) as MorningBriefingResponse
        setBriefing(data)
      } catch {
        setBriefing(null)
      } finally {
        setIsLoading(false)
      }
    }

    loadBriefing()
  }, [isVisible])

  const name = briefing?.name?.trim() || "Ajay"
  const chaosScore = Math.min(10, Math.max(1, Math.round(briefing?.chaos_score ?? 6)))
  const recommendations = useMemo(
    () => (briefing?.recommendations?.slice(0, 3) ?? DEFAULT_RECOMMENDATIONS).slice(0, 3),
    [briefing?.recommendations]
  )

  if (!isVisible) return null

  if (isLoading) {
    return (
      <section className="mb-4 rounded-2xl border border-cyan-200/60 bg-gradient-to-br from-cyan-100 via-white to-emerald-100 p-5 shadow-sm dark:border-cyan-800/70 dark:from-cyan-950/50 dark:via-gray-900 dark:to-emerald-950/40">
        <div className="space-y-3">
          <div className="h-4 w-36 animate-pulse rounded bg-cyan-200/80 dark:bg-cyan-800/70" />
          <div className="h-7 w-56 animate-pulse rounded bg-cyan-200/70 dark:bg-cyan-800/60" />
          <div className="h-16 animate-pulse rounded-lg bg-white/80 dark:bg-gray-800/70" />
          <div className="h-16 animate-pulse rounded-lg bg-white/70 dark:bg-gray-800/60" />
          <div className="h-16 animate-pulse rounded-lg bg-white/70 dark:bg-gray-800/60" />
        </div>
      </section>
    )
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="mb-4 rounded-2xl border border-cyan-200/60 bg-gradient-to-br from-cyan-100 via-white to-emerald-100 p-5 shadow-sm dark:border-cyan-800/70 dark:from-cyan-950/50 dark:via-gray-900 dark:to-emerald-950/40"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700/80 dark:text-cyan-300/80">
            Morning Briefing
          </p>
          <h2 className="mt-1 text-xl font-semibold text-gray-900 dark:text-white">Good Morning, {name}</h2>
        </div>

        <div className="rounded-xl border border-orange-200 bg-orange-50 px-3 py-2 text-right dark:border-orange-800 dark:bg-orange-950/40">
          <p className="text-[11px] uppercase tracking-wide text-orange-700 dark:text-orange-300">Chaos Score</p>
          <p className="text-lg font-bold text-orange-700 dark:text-orange-300">{chaosScore}/10</p>
        </div>
      </div>

      <div className="mt-4 space-y-2.5">
        {recommendations.map((item, idx) => (
          <div
            key={`${item}-${idx}`}
            className="rounded-lg border border-cyan-200/70 bg-white/70 px-3 py-2.5 text-sm text-gray-800 backdrop-blur-sm dark:border-cyan-800/70 dark:bg-gray-900/60 dark:text-gray-100"
          >
            <span className="mr-2 rounded-full bg-cyan-600 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white">
              Action {idx + 1}
            </span>
            {item}
          </div>
        ))}
      </div>
    </motion.section>
  )
}
