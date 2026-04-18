"use client"

import { useState, useEffect, useRef } from "react"
import { postAgent } from "@/lib/api"

interface Message {
  role: "user" | "agent"
  text: string
}

const SUGGESTIONS = [
  "Show me my workouts",
  "How many steps today?",
  "Analyze my health trends",
]

export default function HealthChatBox() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)

  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  async function send(text: string) {
    if (!text.trim()) return

    const userMsg: Message = { role: "user", text: text.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setLoading(true)

    try {
      const response = await postAgent("/api/health/chat", {
        message: text.trim(),
      })

      const reply =
        typeof response.summary === "string" && response.summary.trim()
          ? response.summary
          : "No meaningful response from agent."

      setMessages((prev) => [...prev, { role: "agent", text: reply }])
    } catch (err) {
      console.error("Health chat error:", err)
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "Unable to fetch data. Please try again." },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Ask Health Agent</p>

      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {messages.length > 0 && (
        <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
          {messages.map((m, i) => (
            <div key={`${m.role}-${m.text}-${i}`} className={`text-sm ${m.role === "user" ? "text-right" : ""}`}>
              {m.role === "user" ? (
                <span className="inline-block bg-indigo-600 text-white rounded-lg px-3 py-2 max-w-[80%] text-left">
                  {m.text}
                </span>
              ) : (
                <span className="inline-block max-w-[90%] rounded-lg bg-gray-100 px-3 py-2 text-left text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                  {m.text}
                </span>
              )}
            </div>
          ))}
          {loading && (
            <div className="text-sm">
              <span className="inline-block rounded-lg bg-gray-100 px-3 py-2 text-gray-500 dark:bg-gray-800 dark:text-gray-500">
                Thinking...
              </span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
        className="flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your health..."
          className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 transition-colors focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:placeholder-gray-600"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm px-4 py-2 rounded-lg transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  )
}
