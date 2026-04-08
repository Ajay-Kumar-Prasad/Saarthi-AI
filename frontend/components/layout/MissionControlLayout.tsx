"use client"

import { FormEvent, ReactNode, useState } from "react"
import StreamingChatPanel from "@/components/chat/StreamingChatPanel"

type MissionControlLayoutProps = {
  chatFeed?: ReactNode
  contextPanel?: ReactNode
  onSendMessage?: (message: string) => void
  onPrivacyKillSwitch?: () => void
}

const NAV_ITEMS = ["Work", "Health", "Finance", "Learning", "Social"]

export default function MissionControlLayout({
  chatFeed,
  contextPanel,
  onSendMessage,
  onPrivacyKillSwitch,
}: MissionControlLayoutProps) {
  const [input, setInput] = useState("")

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const message = input.trim()
    if (!message) return
    onSendMessage?.(message)
    setInput("")
  }

  const shouldUseStreamingPanel = !chatFeed && !onSendMessage

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

        <main className="flex min-h-[60vh] flex-col bg-gray-50 dark:bg-gray-950 lg:col-span-3 lg:min-h-screen">
          {shouldUseStreamingPanel ? (
            <StreamingChatPanel />
          ) : (
            <>
              <div className="flex-1 overflow-y-auto p-6">
                {chatFeed ?? (
                  <div className="rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                    Chat feed goes here
                  </div>
                )}
              </div>

              <form
                onSubmit={handleSubmit}
                className="border-t border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
              >
                <div className="flex gap-2">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message..."
                    className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim()}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </form>
            </>
          )}
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
