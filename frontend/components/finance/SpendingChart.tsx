"use client"

type CategoryTotal = {
  category: string
  total: number
}

type SpendingChartProps = {
  data: CategoryTotal[]
  loading?: boolean
}

export default function SpendingChart({ data, loading = false }: SpendingChartProps) {
  if (loading) {
    return <div className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900">Loading summary...</div>
  }

  if (data.length === 0) {
    return <div className="rounded-xl border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">No summary data available yet.</div>
  }

  const total = data.reduce((sum, row) => sum + row.total, 0)
  const sorted = [...data].sort((a, b) => b.total - a.total)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <p className="mb-3 text-sm font-medium text-gray-900 dark:text-white">Spending by Category</p>
      <div className="space-y-2">
        {sorted.map((row) => {
          const percentage = total > 0 ? (row.total / total) * 100 : 0
          return (
            <div key={row.category} className="space-y-1">
              <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-300">
                <span className="capitalize">{row.category}</span>
                <span>
                  Rs {row.total.toLocaleString("en-IN")} ({percentage.toFixed(1)}%)
                </span>
              </div>
              <div className="h-2 rounded bg-gray-100 dark:bg-gray-800">
                <progress
                  className="h-2 w-full overflow-hidden rounded [&::-webkit-progress-bar]:bg-gray-100 [&::-webkit-progress-value]:bg-indigo-500 dark:[&::-webkit-progress-bar]:bg-gray-800"
                  value={percentage}
                  max={100}
                />
              </div>
            </div>
          )
        })}
      </div>
      <p className="mt-4 text-sm font-semibold text-gray-900 dark:text-white">
        Total: Rs {total.toLocaleString("en-IN")}
      </p>
    </div>
  )
}