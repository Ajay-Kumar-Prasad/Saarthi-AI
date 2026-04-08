"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts"
import type { DailyMetric } from "@/lib/health-api"
import { format, parseISO } from "date-fns"

interface Props {
  metrics: DailyMetric[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: <span className="text-white font-medium">{p.value?.toLocaleString()}</span>
        </p>
      ))}
    </div>
  )
}

export default function StepsCaloriesChart({ metrics }: Props) {
  const data = [...metrics]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((m) => ({
      date: format(parseISO(m.date), "MMM d"),
      Steps: m.total_steps ?? 0,
      Calories: m. total_calories ?? 0,
    }))

  if (!data.length) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <p className="text-gray-400 text-xs uppercase tracking-wide mb-4">Steps &amp; Calories</p>
        <p className="text-gray-600 text-sm">No daily metric data available.</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-gray-400 text-xs uppercase tracking-wide mb-4">Steps &amp; Calories — Daily</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} barGap={3}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            yAxisId="steps"
            orientation="left"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          />
          <YAxis
            yAxisId="cal"
            orientation="right"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#1f2937" }} />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "#9ca3af", paddingTop: 8 }}
          />
          <Bar yAxisId="steps" dataKey="Steps" fill="#6366f1" radius={[3, 3, 0, 0]} maxBarSize={20} />
          <Bar yAxisId="cal" dataKey="Calories" fill="#10b981" radius={[3, 3, 0, 0]} maxBarSize={20} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
