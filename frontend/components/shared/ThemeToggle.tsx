"use client"

import { useTheme } from "@/components/shared/ThemeProvider"
import { Sun, Moon } from "lucide-react"

export default function ThemeToggle() {
  const { hydrated, theme, setTheme } = useTheme()

  const dark = theme === "dark"
  const label = !hydrated ? "Theme" : dark ? "Light" : "Dark"

  return (
    <button
      onClick={() => setTheme(dark ? "light" : "dark")}
      type="button"
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-sm text-gray-600 dark:text-gray-400"
      title="Toggle theme"
      aria-pressed={hydrated ? dark : undefined}
    >
      <span className="flex items-center">
        {!hydrated ? null : dark ? <Sun size={16} /> : <Moon size={16} />}
      </span>
      <span className="text-xs font-medium">{label}</span>
    </button>
  )
}
