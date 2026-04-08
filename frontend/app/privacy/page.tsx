"use client"

import { useState } from "react"

export default function PrivacyPage() {
  const [isConfirmOpen, setIsConfirmOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  async function handleDeleteAllData() {
    setIsDeleting(true)
    setStatusMessage(null)

    try {
      const res = await fetch("/api/user/delete", { method: "DELETE" })
      if (!res.ok) throw new Error("Delete failed")
      setStatusMessage("All your data has been deleted.")
    } catch {
      setStatusMessage("Could not delete your data. Please try again.")
    } finally {
      setIsDeleting(false)
      setIsConfirmOpen(false)
    }
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Privacy</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Control your Saarthi memory and personal data lifecycle.</p>
      </div>

      <section className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Database Status</p>
        <p className="mt-2 text-base font-medium text-emerald-600 dark:text-emerald-400">Connected to AlloyDB</p>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Vector Memory</p>
        <p className="mt-2 text-base font-medium text-gray-900 dark:text-white">342 events indexed</p>
      </section>

      <section className="rounded-xl border border-red-200 bg-red-50/40 p-5 dark:border-red-800 dark:bg-red-950/20">
        <p className="text-xs font-semibold uppercase tracking-wide text-red-600 dark:text-red-300">Danger Zone</p>
        <p className="mt-2 text-sm text-red-700/90 dark:text-red-200/90">This action permanently removes your stored profile data, logs, and vector memory.</p>
        <button
          type="button"
          onClick={() => setIsConfirmOpen(true)}
          className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500"
        >
          Delete All My Data
        </button>
      </section>

      {statusMessage && (
        <p className="text-sm text-gray-600 dark:text-gray-300">{statusMessage}</p>
      )}

      {isConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-5 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Confirm Deletion</h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              Are you sure you want to delete all your data? This cannot be undone.
            </p>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsConfirmOpen(false)}
                disabled={isDeleting}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 disabled:opacity-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteAllData}
                disabled={isDeleting}
                className="rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500 disabled:opacity-50"
              >
                {isDeleting ? "Deleting..." : "Confirm Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
