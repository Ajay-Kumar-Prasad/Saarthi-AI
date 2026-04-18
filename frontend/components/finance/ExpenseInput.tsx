"use client"

import { FormEvent, useState } from "react"
import { postAgent } from "@/lib/api"
import { AgentResponse } from "@/types/agent"

const USER_ID = "chjoshna145@gmail.com"

type ExpenseInputProps = {
  onResponse: (response: AgentResponse) => void
}

export default function ExpenseInput({ onResponse }: ExpenseInputProps) {
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const nextMessage = message.trim()
    if (!nextMessage || loading) return

    setLoading(true)
    const response = await postAgent("/api/finance/chat", {
      user_id: USER_ID,
      message: nextMessage,
    })
    onResponse(response)
    setMessage("")
    setLoading(false)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
    >
      <label className="mb-2 block text-sm font-medium text-gray-900 dark:text-white">
        Ask Finance Agent
      </label>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder='e.g. "spent 450 on lunch"'
        />
        <button
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white disabled:opacity-60"
          disabled={loading || !message.trim()}
          type="submit"
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>
    </form>
  )
}