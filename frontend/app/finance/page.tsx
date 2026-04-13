"use client"

import { useState } from "react"
import ExpenseFeed from "@/components/finance/ExpenseFeed"
import ExpenseInput from "@/components/finance/ExpenseInput"
import GmailSyncButton from "@/components/finance/GmailSyncButton"
import SpendingChart from "@/components/finance/SpendingChart"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { getAgent, postAgent } from "@/lib/api"
import { AgentResponse } from "@/types/agent"

type ExpenseRow = {
  id?: string | number
  category?: string
  amount?: number
  expense_date?: string
  description?: string
}

type CategoryTotal = {
  category: string
  total: number
}

function asExpenses(response: AgentResponse | null): ExpenseRow[] {
  const payload = response?.data as Record<string, unknown> | null | undefined
  const list = payload?.expenses
  return Array.isArray(list) ? (list as ExpenseRow[]) : []
}

function asSummary(response: AgentResponse | null): CategoryTotal[] {
  const payload = response?.data as Record<string, unknown> | null | undefined
  const summary = payload?.summary
  if (!Array.isArray(summary)) return []
  return summary
    .map((row) => {
      const item = row as Record<string, unknown>
      const category = typeof item.category === "string" ? item.category : ""
      const total = typeof item.total === "number" ? item.total : 0
      return { category, total }
    })
    .filter((row) => row.category.length > 0)
}

export default function FinancePage() {
  const [activeResponse, setActiveResponse] = useState<AgentResponse | null>(null)
  const [syncResponse, setSyncResponse] = useState<AgentResponse | null>(null)
  const [expensesResponse, setExpensesResponse] = useState<AgentResponse | null>(null)
  const [summaryResponse, setSummaryResponse] = useState<AgentResponse | null>(null)
  const [loading, setLoading] = useState<"idle" | "expenses" | "summary" | "sync">("idle")

  async function loadExpenses() {
    setLoading("expenses")
    const response = await getAgent("/api/finance/expenses")
    setExpensesResponse(response)
    setActiveResponse(response)
    setLoading("idle")
  }

  async function loadSummary() {
    setLoading("summary")
    const response = await getAgent("/api/finance/summary")
    setSummaryResponse(response)
    setActiveResponse(response)
    setLoading("idle")
  }

  function handleChatResponse(response: AgentResponse) {
    setActiveResponse(response)
  }

  function handleSyncResponse(response: AgentResponse) {
    setSyncResponse(response)
    setActiveResponse(response)
    setLoading("idle")
  }

  async function syncGmail() {
    setLoading("sync")
    const response = await postAgent("/api/finance/sync-gmail", {})
    handleSyncResponse(response)
  }

  const expenses = asExpenses(expensesResponse)
  const summary = asSummary(summaryResponse)

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Finance Agent</h1>
        <p className="text-sm text-gray-500">Track expenses, review summary, and sync transactions.</p>
      </div>

      <ExpenseInput onResponse={handleChatResponse} />

      <div className="flex flex-wrap gap-2">
        <button
          onClick={loadExpenses}
          disabled={loading !== "idle"}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          {loading === "expenses" ? "Loading..." : "Load Expenses"}
        </button>
        <button
          onClick={loadSummary}
          disabled={loading !== "idle"}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          {loading === "summary" ? "Loading..." : "Load Summary"}
        </button>
        <GmailSyncButton
          loading={loading === "sync"}
          onClick={syncGmail}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ExpenseFeed expenses={expenses} loading={loading === "expenses"} />
        <SpendingChart data={summary} loading={loading === "summary"} />
      </div>

      {activeResponse ? (
        <AgentResponsePanel title="Finance Agent Response" response={activeResponse} />
      ) : (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
          No agent response yet. Ask a question or load data to begin.
        </div>
      )}

      {syncResponse && <AgentResponsePanel title="Gmail Sync Status" response={syncResponse} />}
    </div>
  )
}