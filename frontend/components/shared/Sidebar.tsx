"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import ThemeToggle from "./ThemeToggle"

const nav = [
  { href: "/", label: "Dashboard", icon: "▦" },
  { href: "/learning", label: "Learning", icon: "📚" },
  { href: "/work", label: "Work", icon: "💼" },
  { href: "/health", label: "Health", icon: "❤️" },
  { href: "/finance", label: "Finance", icon: "💰", disabled: true },
  { href: "/social", label: "Social", icon: "👥", disabled: true },
]

export default function Sidebar() {
  const path = usePathname()
  return (
    <aside className="w-56 min-h-screen bg-white dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800 flex flex-col py-6 px-3 shrink-0">
      <div className="px-3 mb-8">
        <p className="text-gray-900 dark:text-white font-semibold text-lg tracking-tight">Saarthi AI</p>
        <p className="text-gray-500 text-xs mt-0.5">सारथी · Your guide</p>
      </div>

      <nav className="flex flex-col gap-1 flex-1">
        {nav.map((item) => {
          const active = path === item.href
          return item.disabled ? (
            <div key={item.href}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 dark:text-gray-600 cursor-not-allowed text-sm">
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
              <span className="ml-auto text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-600 px-1.5 py-0.5 rounded">soon</span>
            </div>
          ) : (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${active ? "bg-indigo-600 text-white" : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="px-1 mb-4">
        <ThemeToggle />
      </div>

      <div className="px-3 pt-4 border-t border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-semibold">A</div>
          <div>
            <p className="text-gray-900 dark:text-white text-xs font-medium">Ajay Kumar</p>
            <p className="text-gray-500 text-xs">Learning Agent</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
