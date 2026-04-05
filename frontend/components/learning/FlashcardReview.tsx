"use client"
import { useState } from "react"
import { api } from "@/lib/api"

export default function FlashcardReview() {
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
      setCards(list)
      setCurrent(0)
      setFlipped(false)
      setDone(false)
    } finally {
      setLoading(false)
    }
  }

  function next() {
    if (current + 1 >= cards.length) { setDone(true); return }
    setCurrent(current + 1)
    setFlipped(false)
  }

  if (!cards.length) return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h3 className="text-white font-medium mb-4">Flashcard Review</h3>
      <button onClick={load} disabled={loading}
        className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors">
        {loading ? "Loading cards…" : "Load due cards"}
      </button>
    </div>
  )

  if (done) return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <p className="text-green-400 font-medium mb-2">Session complete!</p>
      <p className="text-gray-400 text-sm mb-4">You reviewed {cards.length} cards.</p>
      <button onClick={load} className="px-4 py-2 bg-gray-800 text-white text-sm rounded-lg hover:bg-gray-700">
        Review again
      </button>
    </div>
  )

  const card = cards[current]
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-medium">Flashcard Review</h3>
        <span className="text-gray-500 text-xs">{current + 1} / {cards.length}</span>
      </div>
      <div
        onClick={() => setFlipped(!flipped)}
        className="min-h-32 bg-gray-800 rounded-xl p-5 cursor-pointer flex items-center justify-center text-center transition-all hover:bg-gray-750">
        <p className="text-white text-sm leading-relaxed">
          {flipped ? card.answer : card.question}
        </p>
      </div>
      <p className="text-gray-600 text-xs text-center mt-2">
        {flipped ? "Answer" : "Tap to reveal answer"}
      </p>
      {flipped && (
        <div className="flex gap-2 mt-4">
          {[
            { label: "Hard", q: 1, color: "bg-red-900 hover:bg-red-800 text-red-300" },
            { label: "OK", q: 3, color: "bg-yellow-900 hover:bg-yellow-800 text-yellow-300" },
            { label: "Easy", q: 5, color: "bg-green-900 hover:bg-green-800 text-green-300" },
          ].map(({ label, color }) => (
            <button key={label} onClick={next}
              className={`flex-1 py-2 text-sm rounded-lg transition-colors ${color}`}>
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
