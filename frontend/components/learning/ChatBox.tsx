"use client"
import { useState, useRef, useEffect } from "react"
import { api } from "@/lib/api"

type Msg = { role: "user" | "agent"; text: string; conflicts?: string[] }

const SUGGESTIONS = [
  "What am I currently studying?",
  "What skills am I missing for Data Engineer?",
  "Schedule 1 hour of Python study tomorrow",
  "Show my flashcards due today",
  "I want to become a Cloud Engineer",
]

export default function ChatBox() {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }) }, [msgs])

  async function send(text: string) {
    if (!text.trim() || loading) return
    const userMsg: Msg = { role: "user", text }
    setMsgs((m) => [...m, userMsg])
    setInput("")
    setLoading(true)
    try {
      const res = await api.learning.chat(text)
      const agentMsg: Msg = {
        role: "agent",
        text: res.summary ?? "Done.",
        conflicts: res.conflicts ?? [],
      }
      setMsgs((m) => [...m, agentMsg])
    } catch {
      setMsgs((m) => [...m, { role: "agent", text: "Something went wrong. Is the API running?" }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col h-[480px]">
      <div className="px-5 py-3 border-b border-gray-800">
        <h3 className="text-white font-medium text-sm">Learning Agent Chat</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {msgs.length === 0 && (
          <div className="space-y-2">
            <p className="text-gray-500 text-xs mb-3">Try asking:</p>
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)}
                className="block w-full text-left text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-750 px-3 py-2 rounded-lg transition-colors">
                {s}
              </button>
            ))}
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm leading-relaxed
              ${m.role === "user"
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-200"}`}>
              <p>{m.text}</p>
              {m.conflicts && m.conflicts.length > 0 && (
                <div className="mt-2 space-y-1">
                  {m.conflicts.map((c, j) => (
                    <p key={j} className="text-yellow-400 text-xs">⚠ {c}</p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-xl px-4 py-2.5">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottom} />
      </div>

      <div className="p-3 border-t border-gray-800 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder="Ask anything about your learning…"
          className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
        />
        <button onClick={() => send(input)} disabled={loading || !input.trim()}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors">
          Send
        </button>
      </div>
    </div>
  )
}
