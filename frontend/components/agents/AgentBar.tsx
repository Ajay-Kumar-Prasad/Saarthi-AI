"use client"

import { motion } from "framer-motion"
import {
  Briefcase,
  GraduationCap,
  HeartPulse,
  Landmark,
  LucideIcon,
  Users,
} from "lucide-react"

type AgentName = "work" | "health" | "finance" | "learning" | "social"

type AgentBarProps = {
  activeAgents: string[]
  isLoading?: boolean
}

type AgentConfig = {
  key: AgentName
  label: string
  icon: LucideIcon
  activeClass: string
  glowClass: string
  tooltip: string
}

const AGENTS: AgentConfig[] = [
  {
    key: "work",
    label: "Work",
    icon: Briefcase,
    activeClass: "text-blue-600 dark:text-blue-400",
    glowClass: "shadow-[0_0_20px_rgba(37,99,235,0.35)]",
    tooltip: "Work Agent triaging deadlines and task priority...",
  },
  {
    key: "health",
    label: "Health",
    icon: HeartPulse,
    activeClass: "text-rose-600 dark:text-rose-400",
    glowClass: "shadow-[0_0_20px_rgba(225,29,72,0.35)]",
    tooltip: "Health Agent analyzing sleep data...",
  },
  {
    key: "finance",
    label: "Finance",
    icon: Landmark,
    activeClass: "text-emerald-600 dark:text-emerald-400",
    glowClass: "shadow-[0_0_20px_rgba(5,150,105,0.35)]",
    tooltip: "Finance Agent scanning spend anomalies...",
  },
  {
    key: "learning",
    label: "Learning",
    icon: GraduationCap,
    activeClass: "text-amber-600 dark:text-amber-400",
    glowClass: "shadow-[0_0_20px_rgba(217,119,6,0.35)]",
    tooltip: "Learning Agent mapping your next study plan...",
  },
  {
    key: "social",
    label: "Social",
    icon: Users,
    activeClass: "text-fuchsia-600 dark:text-fuchsia-400",
    glowClass: "shadow-[0_0_20px_rgba(192,38,211,0.35)]",
    tooltip: "Social Agent checking events and relationship cues...",
  },
]

function normalizeAgents(activeAgents: string[]): Set<AgentName> {
  const normalized = new Set<AgentName>()
  for (const value of activeAgents) {
    const key = value.toLowerCase() as AgentName
    if (AGENTS.some((agent) => agent.key === key)) {
      normalized.add(key)
    }
  }
  return normalized
}

export default function AgentBar({ activeAgents, isLoading = false }: AgentBarProps) {
  const normalized = normalizeAgents(activeAgents)

  return (
    <div className="flex items-center gap-2" aria-label="Active agents">
      {AGENTS.map((agent, index) => {
        const Icon = agent.icon
        const isActive = normalized.has(agent.key)

        return (
          <motion.div
            key={agent.key}
            className={`group relative flex h-9 w-9 items-center justify-center rounded-lg border transition-colors ${
              isActive
                ? "border-current/20 bg-current/10"
                : "border-gray-300 bg-gray-100 text-gray-500 grayscale dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400"
            } ${isActive ? `${agent.activeClass} ${agent.glowClass}` : ""}`}
            title={agent.label}
            initial={false}
            animate={
              isActive && isLoading
                ? {
                    scale: [1, 1.08, 1],
                    opacity: [0.55, 1, 0.55],
                  }
                : {
                    scale: 1,
                    opacity: isActive ? 1 : 0.6,
                  }
            }
            transition={
              isActive && isLoading
                ? {
                    duration: 1,
                    repeat: Number.POSITIVE_INFINITY,
                    ease: "easeInOut",
                    delay: index * 0.14,
                  }
                : {
                    duration: 0.2,
                  }
            }
            whileHover={{ scale: 1.06 }}
          >
            <Icon className="h-4 w-4" />
            <div className="pointer-events-none absolute -top-11 left-1/2 z-20 w-max -translate-x-1/2 rounded-md bg-gray-900 px-2 py-1 text-[11px] text-white opacity-0 transition-opacity duration-200 group-hover:opacity-100 dark:bg-gray-100 dark:text-gray-900">
              {agent.tooltip}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

export type { AgentBarProps, AgentName }
