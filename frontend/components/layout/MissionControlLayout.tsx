"use client"

import { ReactNode } from "react"
import StreamingChatPanel from "@/components/chat/StreamingChatPanel"

type MissionControlLayoutProps = {
  chatFeed?: ReactNode
  contextPanel?: ReactNode
  onSendMessage?: (message: string) => void
  onPrivacyKillSwitch?: () => void
}

const NAV_ITEMS = ["Work", "Health", "Finance", "Learning", "Social"]

export default function MissionControlLayout({
  contextPanel,
  onPrivacyKillSwitch,
}: MissionControlLayoutProps) {
  return (
    <div className="min-h-screen w-full bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-white">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-5">
        <aside className="border-b border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900 lg:col-span-1 lg:border-b-0 lg:border-r">
          <p className="mb-4 text-xs font-semibold uppercase tracking-wide text-gray-500">Agents</p>
          <nav className="space-y-2">
            {NAV_ITEMS.map((item) => (
              <button
                key={item}
                type="button"
                className="block w-full rounded-lg border border-gray-200 px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                {item}
              </button>
            ))}
          </nav>

          <button
            type="button"
            onClick={onPrivacyKillSwitch}
            className="mt-6 w-full rounded-lg border border-red-300 bg-red-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500 dark:border-red-800"
          >
            Privacy Kill Switch
          </button>
        </aside>

        <main className="min-h-[60vh] bg-gray-50 dark:bg-gray-950 lg:col-span-3 lg:min-h-screen">
          <div className="flex h-full flex-col">
            <StreamingChatPanel />
          </div>
        </main>

        <aside className="hidden border-l border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900 lg:col-span-1 lg:flex lg:flex-col">
          {contextPanel ?? (
            <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
              Context will appear here
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
