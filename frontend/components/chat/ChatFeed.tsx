"use client"

import AgentBar from "@/components/agents/AgentBar"
import { AnimatePresence, motion } from "framer-motion"

type Message = {
  role: "user" | "assistant"
  content: string
  agents?: string[]
  proof?: Record<string, unknown>
}

type ChatFeedProps = {
  messages: Message[]
  isStreaming?: boolean
  streamingAgents?: string[]
}

export default function ChatFeed({
  messages,
  isStreaming = false,
  streamingAgents = [],
}: ChatFeedProps) {
  const latestUserIndex = [...messages]
    .map((m, i) => ({ m, i }))
    .filter(({ m }) => m.role === "user")
    .map(({ i }) => i)
    .pop()

  return (
    <div className="space-y-3">
      <AnimatePresence initial={false}>
      {messages.map((message, index) => {
        const isUser = message.role === "user"
        const showStreamingState = isStreaming && isUser && index === latestUserIndex
        const activeAgents = showStreamingState
          ? streamingAgents
          : (message.agents ?? [])

        return (
          <motion.div
            key={`${message.role}-${index}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className={`flex ${isUser ? "justify-end" : "justify-start"}`}
          >
            <div className="max-w-[85%]">
              <div
                className={`rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                  isUser
                    ? "bg-indigo-600 text-white"
                    : "border border-gray-200 bg-white text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
                }`}
              >
                {message.role === "assistant" && !message.content.trim() ? (
                  <div className="space-y-2 py-1">
                    <div className="h-2 w-36 animate-pulse rounded bg-gray-300/80 dark:bg-gray-700" />
                    <div className="h-2 w-28 animate-pulse rounded bg-gray-300/70 dark:bg-gray-700/80" />
                  </div>
                ) : (
                  message.content
                )}
              </div>

              {isUser && (
                <div className="mt-2">
                  <AgentBar activeAgents={activeAgents} isLoading={showStreamingState} />
                </div>
              )}
            </div>
          </motion.div>
        )
      })}
      </AnimatePresence>
    </div>
  )
}

export type { Message }
