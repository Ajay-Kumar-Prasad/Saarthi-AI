"use client"

type GmailSyncButtonProps = {
  loading: boolean
  onClick: () => void
}

export default function GmailSyncButton({ loading, onClick }: GmailSyncButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
    >
      {loading ? "Syncing..." : "Sync Gmail"}
    </button>
  )
}