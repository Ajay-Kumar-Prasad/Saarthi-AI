"use client"

import { FormEvent, useState } from "react"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { postAgent } from "@/lib/api"
import { AgentResponse, fallbackAgentResponse } from "@/types/agent"

const USER_ID = "chjoshna145@gmail.com"

export default function WorkPage() {
  const [input, setInput] = useState("Show my work status")
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<AgentResponse | null>(null)

  async function runQuery(message: string) {
    setLoading(true)
    try {
      const result = await postAgent("/api/work/chat", { message, user_id: USER_ID })
      setResponse(result)
    } catch {
      setResponse(fallbackAgentResponse("work_agent", "Unable to fetch data. Please try again."))
    } finally {
      setLoading(false)
    }
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const message = input.trim()
    if (!message || loading) return
    await runQuery(message)
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Work Agent Dashboard</h1>
        <p className="text-sm text-gray-500">Tasks, meetings, and email insights in one place.</p>
      </div>

      <form onSubmit={onSubmit} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">Ask Work Agent</p>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about tasks, meetings, or emails"
            className="flex-1 rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-indigo-600 text-white px-4 py-2 text-sm disabled:opacity-50"
          >
            {loading ? "Analyzing your work data..." : "Send"}
          </button>
        </div>
      </form>

      {loading && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400">
          Loading work insights...
        </div>
      )}

      {response && <AgentResponsePanel title="Work Response" response={response} />}

      {!loading && !response && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-400">
          Ask a question to get a work summary.
        </div>
      )}
    </div>
  )
}
