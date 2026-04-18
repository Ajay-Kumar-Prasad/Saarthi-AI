"use client"

type ExpenseRow = {
  id?: string | number
  category?: string
  amount?: number
  expense_date?: string
  description?: string
}

type ExpenseFeedProps = {
  expenses: ExpenseRow[]
  loading?: boolean
  emptyMessage?: string
}

export default function ExpenseFeed({
  expenses,
  loading = false,
  emptyMessage = "No expenses recorded yet.",
}: ExpenseFeedProps) {
  if (loading) {
    return <div className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900">Loading expenses...</div>
  }

  if (expenses.length === 0) {
    return <div className="rounded-xl border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">{emptyMessage}</div>
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <p className="mb-3 text-sm font-medium text-gray-900 dark:text-white">Recent Expenses</p>
      <div className="space-y-2">
        {expenses.map((item, index) => (
          <div
            key={item.id ?? `${item.category ?? "expense"}-${index}`}
            className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2 dark:border-gray-800"
          >
            <div>
              <p className="text-sm font-medium capitalize text-gray-900 dark:text-white">
                {item.category ?? "Uncategorized"}
              </p>
              <p className="text-xs text-gray-500">
                {item.description ?? "No description"}
                {item.expense_date ? ` • ${item.expense_date}` : ""}
              </p>
            </div>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">
              {typeof item.amount === "number" ? `Rs ${item.amount.toLocaleString("en-IN")}` : "-"}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}