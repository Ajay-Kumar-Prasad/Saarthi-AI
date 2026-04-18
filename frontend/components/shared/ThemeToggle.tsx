"use client"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted) return null

  const dark = theme === "dark"
  return (
    <button
      onClick={() => setTheme(dark ? "light" : "dark")}
      className="flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 transition-colors text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800"
      title="Toggle theme"
    >
      <span className="text-base">{dark ? "☀️" : "🌙"}</span>
      <span className="text-xs font-medium">{dark ? "Switch to Light" : "Switch to Dark"}</span>
    </button>
  )
}
