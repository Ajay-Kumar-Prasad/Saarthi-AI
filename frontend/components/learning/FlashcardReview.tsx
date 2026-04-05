"use client"
import { useState } from "react"
import { api } from "@/lib/api"

type Tab = "review" | "create"

const USER_ID = "00000000-0000-0000-0000-000000000001"

async function createFlashcard(question: string, answer: string, resourceId: string) {
  const res = await fetch("/api/learning/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: USER_ID,
      message: `Create a flashcard: question="${question}", answer="${answer}", resource_id=${resourceId}`,
    }),
  })
  if (!res.ok) throw new Error("Failed")
  return res.json()
}

// ── Review tab ────────────────────────────────────────────────────────────────

function ReviewTab() {
  const [cards, setCards] = useState<{ question: string; answer: string }[]>([])
  const [current, setCurrent] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const res = await api.learning.flashcards()
      const raw = (res?.data as Record<string, unknown>)?.cards
      const list = Array.isArray(raw) ? raw as { question: string; answer: string }[] : []
      setCards(list); setCurrent(0); setFlipped(false); setDone(false)
    } finally { setLoading(false) }
  }

  function next() {
    if (current + 1 >= cards.length) { setDone(true); return }
    setCurrent(current + 1); setFlipped(false)
  }

  if (done) return (
    <div className="text-center py-4">
      <div className="text-3xl mb-2">🎉</div>
      <p className="text-green-600 dark:text-green-400 font-semibold mb-1">Session complete!</p>
      <p className="text-gray-500 text-sm mb-4">Reviewed {cards.length} card{cards.length !== 1 ? "s" : ""}</p>
      <button onClick={load} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-white text-sm rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
        Review again
      </button>
    </div>
  )

  if (!cards.length) return (
    <div>
      <p className="text-gray-500 text-xs mb-4">SM-2 spaced repetition · cards due today</p>
      <button onClick={load} disabled={loading}
        className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors font-medium">
        {loading ? "Loading cards…" : "Load due cards"}
      </button>
    </div>
  )

  const card = cards[current]
  return (
    <div>
      <div className="flex justify-end mb-3">
        <span className="text-gray-400 text-xs bg-gray-100 dark:bg-gray-800 px-2.5 py-1 rounded-full">
          {current + 1} / {cards.length}
        </span>
      </div>

      <div onClick={() => setFlipped(!flipped)}
        className={`min-h-36 rounded-xl p-5 cursor-pointer flex items-center justify-center text-center transition-all border-2
          ${flipped
            ? "bg-indigo-50 dark:bg-indigo-950/30 border-indigo-200 dark:border-indigo-800"
            : "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-700"
          }`}>
        <div>
          <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">{flipped ? "Answer" : "Question"}</p>
          <p className="text-gray-900 dark:text-white text-sm leading-relaxed font-medium">
            {flipped ? card.answer : card.question}
          </p>
        </div>
      </div>

      {!flipped && <p className="text-gray-400 text-xs text-center mt-2">Tap card to reveal answer</p>}

      {flipped && (
        <div className="flex gap-2 mt-4">
          {[
            { label: "Hard", color: "bg-red-50 dark:bg-red-950 hover:bg-red-100 dark:hover:bg-red-900 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800" },
            { label: "OK",   color: "bg-yellow-50 dark:bg-yellow-950 hover:bg-yellow-100 dark:hover:bg-yellow-900 text-yellow-600 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800" },
            { label: "Easy", color: "bg-green-50 dark:bg-green-950 hover:bg-green-100 dark:hover:bg-green-900 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800" },
          ].map(({ label, color }) => (
            <button key={label} onClick={next}
              className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-colors ${color}`}>
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Create tab ────────────────────────────────────────────────────────────────

function CreateTab() {
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")
  const [resourceId, setResourceId] = useState("")
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  async function handleCreate() {
    if (!question.trim() || !answer.trim() || !resourceId.trim()) return
    setSaving(true)
    setMsg(null)
    try {
      const res = await createFlashcard(question.trim(), answer.trim(), resourceId.trim())
      setMsg({ text: res?.summary ?? "Card created!", ok: true })
      setQuestion("")
      setAnswer("")
    } catch {
      setMsg({ text: "Failed to create card. Is the backend running?", ok: false })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-gray-400 text-xs">Add a new card to your deck</p>

      <div>
        <label className="text-gray-500 text-xs mb-1 block">Resource ID *</label>
        <input
          value={resourceId}
          onChange={(e) => setResourceId(e.target.value)}
          placeholder="e.g. 1"
          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>

      <div>
        <label className="text-gray-500 text-xs mb-1 block">Question *</label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What is a list comprehension in Python?"
          rows={2}
          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
        />
      </div>

      <div>
        <label className="text-gray-500 text-xs mb-1 block">Answer *</label>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="e.g. [expression for item in iterable if condition]"
          rows={2}
          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
        />
      </div>

      {msg && (
        <p className={`text-xs ${msg.ok ? "text-green-400" : "text-red-400"}`}>{msg.text}</p>
      )}

      <button
        onClick={handleCreate}
        disabled={saving || !question.trim() || !answer.trim() || !resourceId.trim()}
        className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
      >
        {saving ? "Creating…" : "Create Flashcard"}
      </button>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function FlashcardReview() {
  const [tab, setTab] = useState<Tab>("review")

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-gray-900 dark:text-white font-semibold">Flashcards</h3>
          <p className="text-gray-400 text-xs mt-0.5">SM-2 spaced repetition</p>
        </div>
        <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5 gap-0.5">
          {(["review", "create"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors capitalize
                ${tab === t
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {tab === "review" ? <ReviewTab /> : <CreateTab />}
    </div>
  )
}