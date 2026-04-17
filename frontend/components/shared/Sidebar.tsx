"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import ThemeToggle from "./ThemeToggle"
import {
  LayoutDashboard,
  BookOpen,
  Briefcase,
  Heart,
  DollarSign,
  Users
} from "lucide-react"

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/learning", label: "Learning", icon: BookOpen },
  { href: "/work", label: "Work", icon: Briefcase },
  { href: "/health", label: "Health", icon: Heart },
  { href: "/finance", label: "Finance", icon: DollarSign },
  { href: "/social", label: "Social", icon: Users },
]

export default function Sidebar() {
  const path = usePathname()

  const isActive = (href: string) => {
    if (href === "/") return path === "/"
    return path === href || path.startsWith(`${href}/`)
  }

  return (
    <aside className="w-56 min-h-screen bg-white dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800 flex flex-col py-6 px-3 shrink-0">
      <div className="px-3 mb-8">
        <p className="text-gray-900 dark:text-white font-semibold text-lg tracking-tight">
          Saarthi AI
        </p>
        <p className="text-gray-500 text-xs mt-0.5">
          सारथी · Your guide
        </p>
      </div>

      <nav className="flex flex-col gap-1 flex-1">
        {nav.map((item) => {
          const active = isActive(item.href)
          const Icon = item.icon

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
              <span>
                <Icon size={18} />
              </span>
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
          <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-semibold">
            S
          </div>
          <div>
            <p className="text-gray-900 dark:text-white text-xs font-medium">
              SaarthiAI
            </p>
          </div>
        </div>
      </div>
    </aside>
  )
}