"use client"
import { useState, useRef, useEffect } from "react"
import { api } from "@/lib/api"

type Msg = { role: "user" | "agent"; text: string; conflicts?: string[]; actions?: string[] }

const SUGGESTIONS = [
  "What am I currently studying?",
  "What skills am I missing for Data Engineer?",
  "Schedule 1 hour of Python study tomorrow",
  "Show my flashcards due today",
  "I want to become a Cloud Engineer",
  "How many hours did I study this week?",
]

// Actions that likely mutate state — trigger a status refresh after these
const MUTATING_KEYWORDS = ["schedule", "add", "create", "mark", "update", "log", "save", "complete"]

export default function ChatBox({ onAction }: { onAction?: () => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }) }, [msgs])

  async function send(text: string) {
    if (!text.trim() || loading) return
    setMsgs((m) => [...m, { role: "user", text }])
    setInput("")
    setLoading(true)
    try {
      const res = await api.learning.chat(text)
      setMsgs((m) => [...m, {
        role: "agent",
        text: res.summary ?? "Done.",
        conflicts: res.conflicts ?? [],
        actions: res.actions_taken ?? [],
      }])
      // Refresh status cards if the message likely mutated data
      const lower = text.toLowerCase()
      if (onAction && MUTATING_KEYWORDS.some((kw) => lower.includes(kw))) {
        onAction()
      }
    } catch {
      setMsgs((m) => [...m, { role: "agent", text: "Something went wrong. Is the API running on port 8080?" }])
    } finally { setLoading(false) }
  }

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl flex flex-col h-[520px]">
      <div className="px-5 py-3.5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
        <div>
          <h3 className="text-gray-900 dark:text-white font-semibold text-sm">Learning Agent</h3>
          <p className="text-gray-400 text-xs">Powered by Gemini · AlloyDB</p>
        </div>
        <div className="w-2 h-2 bg-green-500 rounded-full" title="Agent online" />
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {msgs.length === 0 && (
          <div>
            <p className="text-gray-400 dark:text-gray-500 text-xs mb-3 font-medium">Suggestions:</p>
            <div className="space-y-1.5">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="block w-full text-left text-xs text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 bg-gray-50 dark:bg-gray-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-700 px-3 py-2 rounded-lg transition-all">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[88%] rounded-xl px-4 py-2.5 text-sm leading-relaxed
              ${m.role === "user"
                ? "bg-indigo-600 text-white"
                : "bg-gray-50 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700"}`}>
              <p>{m.text}</p>
              {m.conflicts && m.conflicts.length > 0 && (
                <div className="mt-2 space-y-1 border-t border-yellow-200 dark:border-yellow-900 pt-2">
                  {m.conflicts.map((c, j) => (
                    <p key={j} className="text-yellow-600 dark:text-yellow-400 text-xs flex gap-1.5">
                      <span>⚠</span><span>{c}</span>
                    </p>
                  ))}
                </div>
              )}
              {m.actions && m.actions.length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {m.actions.map((a, j) => (
                    <p key={j} className="text-green-600 dark:text-green-400 text-xs flex gap-1.5">
                      <span>✓</span><span>{a}</span>
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3">
              <div className="flex gap-1 items-center">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
                <span className="text-gray-400 text-xs ml-2">Thinking…</span>
              </div>
            </div>
          </div>
        )}
        <div ref={bottom} />
      </div>

      <div className="p-3 border-t border-gray-100 dark:border-gray-800 flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder="Ask your learning agent…"
          className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white text-sm rounded-lg px-3 py-2 placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors"
        />
        <button onClick={() => send(input)} disabled={loading || !input.trim()}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm rounded-lg transition-colors font-medium">
          Send
        </button>
      </div>
    </div>
  )
}