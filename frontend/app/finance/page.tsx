"use client"

import { useState, useEffect } from "react"
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

/* -------------------- Helpers -------------------- */

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

function getTotalSpend(summary: CategoryTotal[]) {
  return summary.reduce((acc, curr) => acc + curr.total, 0)
}

function getTopCategory(summary: CategoryTotal[]) {
  if (!summary.length) return null
  return summary.reduce((max, curr) =>
    curr.total > max.total ? curr : max
  )
}

function getAvgExpense(expenses: ExpenseRow[]) {
  if (!expenses.length) return 0
  const total = expenses.reduce((sum, e) => sum + (e.amount ?? 0), 0)
  return Math.round(total / expenses.length)
}

/* -------------------- Component -------------------- */

export default function FinancePage() {
  const [activeResponse, setActiveResponse] = useState<AgentResponse | null>(null)
  const [syncResponse, setSyncResponse] = useState<AgentResponse | null>(null)
  const [expensesResponse, setExpensesResponse] = useState<AgentResponse | null>(null)
  const [summaryResponse, setSummaryResponse] = useState<AgentResponse | null>(null)
  const [loading, setLoading] = useState<"idle" | "expenses" | "summary" | "sync">("idle")

  /* 🔥 AUTO LOAD DATA */
  useEffect(() => {
    async function init() {
      setLoading("expenses")

      try {
        const [expensesRes, summaryRes] = await Promise.all([
          getAgent("/api/finance/expenses"),
          getAgent("/api/finance/summary"),
        ])

        setExpensesResponse(expensesRes)
        setSummaryResponse(summaryRes)
        setActiveResponse(summaryRes)
      } finally {
        setLoading("idle")
      }
    }

    init()
  }, [])

  async function refreshExpenses() {
    setLoading("expenses")
    const response = await getAgent("/api/finance/expenses")
    setExpensesResponse(response)
    setActiveResponse(response)
    setLoading("idle")
  }

  async function refreshSummary() {
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

  const totalSpend = getTotalSpend(summary)
  const topCategory = getTopCategory(summary)
  const avgExpense = getAvgExpense(expenses)

  return (
    <div className="space-y-6 p-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Finance Agent
        </h1>
        <p className="text-sm text-gray-500">
          Track expenses, analyze spending, and sync transactions.
        </p>
      </div>

      {/* 🔥 Analytics Cards */}
      {summary.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-500">Total Spend</p>
            <p className="text-xl font-semibold text-gray-900 dark:text-white">
              ₹{totalSpend.toLocaleString()}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-500">Top Category</p>
            <p className="text-xl font-semibold text-indigo-600 dark:text-indigo-400">
              {topCategory?.category ?? "—"}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-500">Avg Expense</p>
            <p className="text-xl font-semibold text-gray-900 dark:text-white">
              ₹{avgExpense.toLocaleString()}
            </p>
          </div>

        </div>
      )}

      {/* Input */}
      <ExpenseInput onResponse={handleChatResponse} />

      {/* Actions (now refresh, not load) */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={refreshExpenses}
          disabled={loading !== "idle"}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          {loading === "expenses" ? "Refreshing..." : "Refresh Expenses"}
        </button>

        <button
          onClick={refreshSummary}
          disabled={loading !== "idle"}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          {loading === "summary" ? "Refreshing..." : "Refresh Summary"}
        </button>

        <GmailSyncButton
          loading={loading === "sync"}
          onClick={syncGmail}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

        <ExpenseFeed
          expenses={expenses}
          loading={loading === "expenses"}
        />

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
          <p className="text-sm text-gray-500 mb-3">
            Category Breakdown
          </p>
          <SpendingChart
            data={summary}
            loading={loading === "summary"}
          />
        </div>

      </div>

      {/* Response Panel */}
      {activeResponse ? (
        <AgentResponsePanel
          title="Finance Agent Response"
          response={activeResponse}
        />
      ) : (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 text-center">
          <p className="text-gray-500 text-sm">
            Start by asking the Finance Agent something useful.
          </p>
        </div>
      )}

      {/* Sync Response */}
      {syncResponse && (
        <AgentResponsePanel
          title="Gmail Sync Status"
          response={syncResponse}
        />
      )}

    </div>
  )
}