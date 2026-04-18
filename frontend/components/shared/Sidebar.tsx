"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { startTransition, useEffect, useState, useSyncExternalStore } from "react"
import ThemeToggle from "./ThemeToggle"

const nav = [
  { href: "/", label: "Dashboard", icon: "▦" },
  { href: "/learning", label: "Learning", icon: "📚" },
  { href: "/work", label: "Work", icon: "💼" },
  { href: "/health", label: "Health", icon: "❤️" },
  { href: "/finance", label: "Finance", icon: "💰" },
  { href: "/social", label: "Social", icon: "👥" },
]

export default function Sidebar() {
  const path = usePathname()
  const [healthUserId, setHealthUserId] = useState<string | null>(null)
  const [healthConnected, setHealthConnected] = useState(false)
  const [emailInput, setEmailInput] = useState("")
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  )

  useEffect(() => {
    const savedEmail = window.localStorage.getItem("health_connect_email")
    if (savedEmail) {
      startTransition(() => {
        setEmailInput(savedEmail)
      })
    }

    void (async () => {
      try {
        const response = await fetch("/api/health/auth-status", {
          cache: "no-store",
        })
        const payload = (await response.json().catch(() => ({}))) as {
          connected?: boolean
          userId?: string | null
        }
        const userId =
          typeof payload.userId === "string" && payload.userId.trim()
            ? payload.userId.trim()
            : null

        setHealthConnected(Boolean(payload.connected && userId))
        setHealthUserId(userId)
        if (userId) {
          setEmailInput(userId)
          window.localStorage.setItem("health_connect_email", userId)
        }
      } catch {
        setHealthConnected(false)
      }
    })()
  }, [])

  const isActive = (href: string) => {
    if (href === "/") return path === "/"
    return path === href || path.startsWith(`${href}/`)
  }

  const connectHref = emailInput.trim()
    ? `/api/health/connect?user_id=${encodeURIComponent(emailInput.trim())}`
    : null

  return (
    <aside className="w-56 min-h-screen bg-white dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800 flex flex-col py-6 px-3 shrink-0">
      <div className="px-3 mb-8">
        <p className="text-gray-900 dark:text-white font-semibold text-lg tracking-tight">Saarthi AI</p>
        <p className="text-gray-500 text-xs mt-0.5">सारथी · Your guide</p>
      </div>

      <nav className="flex flex-col gap-1 flex-1">
        {nav.map((item) => {
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-indigo-600 text-white"
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="mx-1 mb-4 rounded-2xl border border-emerald-200/80 bg-[linear-gradient(135deg,rgba(16,185,129,0.08),rgba(255,255,255,0.98),rgba(59,130,246,0.08))] p-3 dark:border-emerald-900/70 dark:bg-[linear-gradient(135deg,rgba(6,78,59,0.42),rgba(3,7,18,0.92),rgba(30,64,175,0.26))]">
        <div className="mb-2 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">
              Health Access
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              {mounted && healthConnected ? "Connected account ready" : "Connect once for health data"}
            </p>
          </div>
          <div className={`h-2.5 w-2.5 rounded-full ${mounted && healthConnected ? "bg-emerald-500" : "bg-amber-400"}`} />
        </div>

        {!mounted ? (
          <div className="space-y-2">
            <div className="h-10 rounded-xl border border-emerald-200/70 bg-white/80 dark:border-emerald-900/60 dark:bg-black/20" />
            <div className="h-10 rounded-xl bg-gray-200 dark:bg-gray-800" />
          </div>
        ) : healthConnected ? (
          <div className="rounded-xl border border-emerald-200/80 bg-white/85 px-3 py-2 dark:border-emerald-900/60 dark:bg-black/20">
            <p className="truncate text-sm font-medium text-gray-900 dark:text-white">
              {healthUserId}
            </p>
            <Link
              href="/health"
              className="mt-1 inline-flex text-xs font-medium text-emerald-700 hover:text-emerald-600 dark:text-emerald-300 dark:hover:text-emerald-200"
            >
              Open health dashboard
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            <input
              type="email"
              value={emailInput}
              onChange={(e) => {
                const nextValue = e.target.value
                setEmailInput(nextValue)
                window.localStorage.setItem("health_connect_email", nextValue)
              }}
              placeholder="you@example.com"
              className="w-full rounded-xl border border-emerald-200 bg-white/90 px-3 py-2 text-sm text-gray-900 outline-none transition-colors focus:border-emerald-500 dark:border-emerald-900/70 dark:bg-black/20 dark:text-white"
            />
            <a
              href={connectHref ?? "#"}
              aria-disabled={!connectHref}
              className={`inline-flex w-full items-center justify-center rounded-xl px-3 py-2 text-sm font-semibold transition-all ${
                connectHref
                  ? "bg-emerald-500 text-white hover:bg-emerald-400"
                  : "pointer-events-none bg-gray-200 text-gray-500 dark:bg-gray-800 dark:text-gray-500"
              }`}
            >
              Connect Google Fit
            </a>
          </div>
        )}
      </div>

      <div className="px-1 mb-4 pt-1">
        <ThemeToggle />
      </div>

      <div className="px-3 pt-4 border-t border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-semibold">
            {(healthUserId ?? "S").trim().charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-gray-900 dark:text-white text-xs font-medium">
              {healthUserId ?? "Saarthi User"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  )
}
