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
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-700 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-sm text-gray-600 dark:text-gray-400"
      title="Toggle theme"
    >
      <span className="text-base">{dark ? "☀️" : "🌙"}</span>
      <span className="text-xs font-medium">{dark ? "Light" : "Dark"}</span>
    </button>
  )
}
