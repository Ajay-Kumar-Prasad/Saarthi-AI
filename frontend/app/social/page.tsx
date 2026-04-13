"use client"

import { FormEvent, useState } from "react"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { postAgent } from "@/lib/api"
import { AgentResponse } from "@/types/agent"

const USER_ID = "00000000-0000-0000-0000-000000000001"

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

  return (
    <div className="space-y-6 p-8">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Social Agent</h1>
      <p className="text-sm text-gray-500 mt-1">Track events, relationships, and social priorities.</p>

      <form onSubmit={handleSubmit} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
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
            Send
          </button>
        </div>
      </form>

      {loading && <p className="text-sm text-gray-500">Loading...</p>}
      {response && <AgentResponsePanel title="Social Response" response={response} />}
    </div>
  )
}
