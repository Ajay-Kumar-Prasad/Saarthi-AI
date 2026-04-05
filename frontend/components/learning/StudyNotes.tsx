"use client"
import { useState } from "react"
import { api } from "@/lib/api"
import type { Resource } from "@/lib/api"

type Note = { note_id: string; content: string; created_at?: string; resource?: string; doc_url?: string }

export default function StudyNotes({ resources }: { resources: Resource[] }) {
  const [selectedResource, setSelectedResource] = useState<string>("all")
  const [notes, setNotes] = useState<Note[]>([])
  const [noteText, setNoteText] = useState("")
  const [loadingNotes, setLoadingNotes] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  async function loadNotes() {
    setLoadingNotes(true)
    setError(null)
    try {
      const res = await api.learning.chat(
        selectedResource === "all"
          ? "show my notes"
          : `show notes for ${selectedResource}`
      )
      const raw = res?.data as Record<string, unknown> | null
      const list = Array.isArray(raw?.notes) ? (raw!.notes as Note[]) : []
      setNotes(list)
      setLoaded(true)
    } catch {
      setError("Could not load notes.")
    } finally {
      setLoadingNotes(false)
    }
  }

  async function saveNote() {
    if (!noteText.trim()) return
    const resource = selectedResource === "all"
      ? (resources[0]?.title ?? "General")
      : selectedResource
    console.log("SAVING NOTE — resource:", resource, "text:", noteText.trim()) // ← add
    console.log("API call:", `Save this note for ${resource}: ${noteText.trim()}`) // ← add
    setSaving(true)
    setError(null)
    setSaveMsg(null)
    try {
      await api.learning.saveNote(resource, noteText.trim())
      setNotes((prev) => [{
        note_id: crypto.randomUUID(),
        content: noteText.trim(),
        resource: resource,
      }, ...prev])
      setSaveMsg("Note saved!")
      setNoteText("")
      setTimeout(() => setSaveMsg(null), 3000)
    } catch {
      setError("Failed to save note.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-gray-900 dark:text-white font-semibold">Study Notes</h3>
          <p className="text-gray-400 text-xs mt-0.5">Log insights as you learn</p>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <select
          value={selectedResource}
          onChange={(e) => { setSelectedResource(e.target.value); setLoaded(false); setNotes([]) }}
          className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500 transition-colors"
        >
          <option value="all">All resources</option>
          {resources.map((r) => (
            <option key={r.id} value={r.title}>{r.title}</option>
          ))}
        </select>
        <button
          onClick={loadNotes}
          disabled={loadingNotes}
          className="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 text-gray-700 dark:text-white text-sm rounded-lg transition-colors font-medium"
        >
          {loadingNotes ? "Loading…" : loaded ? "Refresh" : "Load Notes"}
        </button>
      </div>

      <div className="mb-4">
        <textarea
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder={`Write a note${selectedResource !== "all" ? ` for ${selectedResource}` : ""}…`}
          rows={3}
          className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
        />
        <div className="flex items-center justify-between mt-2">
          <div>
            {error && <p className="text-red-400 text-xs">{error}</p>}
            {saveMsg && <p className="text-green-400 text-xs">{saveMsg}</p>}
          </div>
          <button
            onClick={saveNote}
            disabled={saving || !noteText.trim()}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors font-medium"
          >
            {saving ? "Saving…" : "Save Note"}
          </button>
        </div>
      </div>

      {loaded && notes.length === 0 && (
        <div className="text-center py-6 border border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
          <p className="text-gray-400 text-sm">No notes yet for this resource.</p>
          <p className="text-gray-500 text-xs mt-1">Write something above to get started.</p>
        </div>
      )}

      {notes.length > 0 && (
        <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
          {notes.map((n, i) => (
            <div key={n.note_id ?? i} className="bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl p-3">
              <p className="text-gray-900 dark:text-white text-sm leading-relaxed">{n.content}</p>
              <div className="flex items-center justify-between mt-2">
                {n.resource && (
                  <span className="text-xs text-indigo-500 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-100 dark:border-indigo-900 px-2 py-0.5 rounded-full">
                    {n.resource}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}