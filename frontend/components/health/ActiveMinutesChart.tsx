"use client"

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import type { DailyMetric } from "@/lib/health-api"
import { format, parseISO } from "date-fns"

type TooltipPayloadItem = { value?: number }
type TooltipProps = { active?: boolean; payload?: TooltipPayloadItem[]; label?: string }

const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <p className="mb-1 text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-indigo-400">
        Active: <span className="font-medium text-gray-900 dark:text-white">{payload[0]?.value} min</span>
      </p>
    </div>
  )
}

export default function ActiveMinutesChart({ metrics }: { metrics: DailyMetric[] }) {
  const data = [...metrics]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((m) => ({
      date: format(parseISO(m.date), "MMM d"),
      "Active Min": m.active_minutes ?? 0,
    }))

  if (!data.length) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <p className="mb-4 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Active Minutes</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">No data available.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
      <p className="mb-4 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Active Minutes — Daily</p>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="actGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={32}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "#374151" }} />
          <Area
            type="monotone"
            dataKey="Active Min"
            stroke="#6366f1"
            strokeWidth={2}
            fill="url(#actGrad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
