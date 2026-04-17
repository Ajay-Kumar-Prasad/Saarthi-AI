"use client"

import { useState, useEffect, useRef } from "react"
import { postAgent } from "@/lib/api"

interface Message {
  role: "user" | "agent"
  text: string
}

const USER_ID = "chjoshna145@gmail.com"

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
        user_id: USER_ID,
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
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-3">
      <p className="text-gray-400 text-xs uppercase tracking-wide">Ask Health Agent</p>

      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 rounded-full px-3 py-1 transition-colors"
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
                <span className="inline-block bg-gray-800 text-gray-300 rounded-lg px-3 py-2 max-w-[90%] text-left">
                  {m.text}
                </span>
              )}
            </div>
          ))}
          {loading && (
            <div className="text-sm">
              <span className="inline-block bg-gray-800 text-gray-500 rounded-lg px-3 py-2">
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
          className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
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