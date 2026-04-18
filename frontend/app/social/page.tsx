"use client"

import { FormEvent, useState } from "react"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { postAgent } from "@/lib/api"
import { AgentResponse } from "@/types/agent"

const USER_ID = "chjoshna145@gmail.com"

/* 🔥 Mock fallback data */
const MOCK_SOCIAL_DATA = {
  upcoming_events: 3,
  pending_connections: 5,
  reminders: 2,
  highlights: [
    "You haven't contacted Rahul in 12 days",
    "3 events scheduled this weekend",
    "Ananya's birthday is coming up",
  ],
}

export default function SocialPage() {
  const [message, setMessage] = useState("Show my social status")
  const [response, setResponse] = useState<AgentResponse | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!message.trim()) return

    setLoading(true)
    const result = await postAgent("/api/social/chat", {
      message: message.trim(),
      user_id: USER_ID,
    })
    setResponse(result)
    setLoading(false)
  }

  function quickAsk(text: string) {
    setMessage(text)
  }

  /* 🔥 Decide real vs mock */
  const hasRealData = !!response?.data
  const socialData = hasRealData
    ? (response?.data as any)
    : MOCK_SOCIAL_DATA

  return (
    <div className="space-y-6 p-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Social Agent
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage relationships, track events, and stay socially aligned.
        </p>
      </div>

      {/* 🔥 Analytics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-500">Upcoming Events</p>
          <p className="text-xl font-semibold text-gray-900 dark:text-white">
            {socialData.upcoming_events ?? "—"}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-500">Pending Connections</p>
          <p className="text-xl font-semibold text-gray-900 dark:text-white">
            {socialData.pending_connections ?? "—"}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-500">Reminders</p>
          <p className="text-xl font-semibold text-gray-900 dark:text-white">
            {socialData.reminders ?? "—"}
          </p>
        </div>

      </div>

      {/* 🔥 Insights Panel */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
        <p className="text-sm text-gray-500 mb-3">Insights</p>

        <ul className="space-y-2">
          {(socialData.highlights ?? []).map((item: string, i: number) => (
            <li
              key={i}
              className="text-sm text-gray-700 dark:text-gray-300"
            >
              • {item}
            </li>
          ))}
        </ul>

        {!hasRealData && (
          <p className="text-xs text-gray-400 mt-3">
            Showing sample insights until real data is available.
          </p>
        )}
      </div>

      {/* ⚡ Quick Actions */}
      <div className="flex flex-wrap gap-2">
        {[
          "Show my social status",
          "Upcoming events this week",
          "People I should reconnect with",
          "Important birthdays coming up",
        ].map((q) => (
          <button
            key={q}
            onClick={() => quickAsk(q)}
            className="text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            {q}
          </button>
        ))}
      </div>

      {/* 💬 Chat */}
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
      >
        <div className="flex gap-2">
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
            placeholder="Ask social agent..."
          />
          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white disabled:opacity-60"
          >
            {loading ? "Thinking..." : "Send"}
          </button>
        </div>
      </form>

      {/* Response */}
      {loading && (
        <p className="text-sm text-gray-500">
          Analyzing your social graph...
        </p>
      )}

      {response && (
        <AgentResponsePanel
          title="Social Insights"
          response={response}
        />
      )}
    </div>
  )
}