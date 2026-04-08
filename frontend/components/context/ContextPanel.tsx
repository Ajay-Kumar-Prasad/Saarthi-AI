"use client"

import { useQuery } from "@tanstack/react-query"
import { BarChart, Card, Title, Text } from "@tremor/react"
import { motion } from "framer-motion"

type AgentName = "work" | "health" | "finance" | "learning" | "social"

type ContextPanelProps = {
  activeAgent: AgentName | string
}

const defaultFinanceData = [
  { month: "Jan", Spend: 42000 },
  { month: "Feb", Spend: 38500 },
  { month: "Mar", Spend: 45100 },
  { month: "Apr", Spend: 39800 },
]

const defaultSleepData = [
  { day: "Mon", SleepHours: 6.5 },
  { day: "Tue", SleepHours: 7.2 },
  { day: "Wed", SleepHours: 5.9 },
  { day: "Thu", SleepHours: 6.8 },
  { day: "Fri", SleepHours: 7.4 },
  { day: "Sat", SleepHours: 8.0 },
  { day: "Sun", SleepHours: 7.1 },
]

function FinanceWidget({ financeData = defaultFinanceData }: { financeData?: Array<{ month: string; Spend: number }> }) {
  return (
    <Card className="rounded-xl">
      <Title>Finance Snapshot</Title>
      <Text className="mb-3">Monthly spending trend</Text>
      <BarChart
        data={financeData}
        index="month"
        categories={["Spend"]}
        colors={["emerald"]}
        yAxisWidth={56}
      />
    </Card>
  )
}

function HealthWidget({ sleepData = defaultSleepData }: { sleepData?: Array<{ day: string; SleepHours: number }> }) {
  return (
    <Card className="rounded-xl">
      <Title>Sleep Trend</Title>
      <Text className="mb-3">Last 7 days of sleep hours</Text>
      <BarChart
        data={sleepData}
        index="day"
        categories={["SleepHours"]}
        colors={["sky"]}
        yAxisWidth={48}
      />
    </Card>
  )
}

function WorkWidget({ tasks }: { tasks: { total: number; dueToday: number; blocked: number; completed: number } }) {
  return (
    <Card className="rounded-xl">
      <Title>Task Summary</Title>
      <Text className="mb-4">Current work queue status</Text>
      <div className="space-y-2 text-sm text-gray-700 dark:text-gray-200">
        <div className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-800">
          <span>Total Tasks</span>
          <span className="font-semibold">{tasks.total}</span>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-950/30">
          <span>Due Today</span>
          <span className="font-semibold">{tasks.dueToday}</span>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-red-50 px-3 py-2 dark:bg-red-950/30">
          <span>Blocked</span>
          <span className="font-semibold">{tasks.blocked}</span>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-green-50 px-3 py-2 dark:bg-green-950/30">
          <span>Completed</span>
          <span className="font-semibold">{tasks.completed}</span>
        </div>
      </div>
    </Card>
  )
}

export default function ContextPanel({ activeAgent }: ContextPanelProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["context", activeAgent],
    queryFn: async () => {
      const res = await fetch(`/api/context?agent=${activeAgent}`)
      if (!res.ok) return null
      return res.json() as Promise<{
        agent: string
        context: {
          financeData?: Array<{ month: string; Spend: number }>
          sleepData?: Array<{ day: string; SleepHours: number }>
          tasks?: { total: number; dueToday: number; blocked: number; completed: number }
        }
      }>
    },
  })

  if (isLoading) {
    return (
      <Card className="rounded-xl">
        <div className="space-y-3">
          <div className="h-4 w-32 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-24 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />
          <div className="h-24 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />
        </div>
      </Card>
    )
  }

  if (activeAgent === "finance") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
        <FinanceWidget financeData={data?.context?.financeData ?? defaultFinanceData} />
      </motion.div>
    )
  }

  if (activeAgent === "health") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
        <HealthWidget sleepData={data?.context?.sleepData ?? defaultSleepData} />
      </motion.div>
    )
  }

  if (activeAgent === "work") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
        <WorkWidget tasks={data?.context?.tasks ?? { total: 18, dueToday: 5, blocked: 2, completed: 11 }} />
      </motion.div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      <Card className="rounded-xl">
        <Title>Context Panel</Title>
        <Text className="mt-2">Select an agent to view contextual insights.</Text>
      </Card>
    </motion.div>
  )
}

export type { ContextPanelProps, AgentName }
