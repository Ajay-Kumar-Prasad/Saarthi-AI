"use client"

import { FormEvent, useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import ChatFeed, { type Message } from "@/components/chat/ChatFeed"
import MorningBriefing from "@/components/dashboard/MorningBriefing"

type StreamingChatPanelProps = {
  activeAgent?: string
}

const ALL_AGENTS = ["work", "health", "finance", "learning", "social"]
const USER_ID = "00000000-0000-0000-0000-000000000001"

function resolveAgents(activeAgent?: string): string[] {
  if (!activeAgent) return ALL_AGENTS
  return [activeAgent.toLowerCase()]
}

export default function StreamingChatPanel({ activeAgent }: StreamingChatPanelProps) {
  console.log("STREAMING CHAT PANEL LOADED")
  const [input, setInput] = useState("")
  const [streamingAgents, setStreamingAgents] = useState<string[]>([])
  const queryClient = useQueryClient()

  const selectedAgents = useMemo(() => resolveAgents(activeAgent), [activeAgent])

  const { data: messages = [] } = useQuery<Message[]>({
    queryKey: ["messages"],
    queryFn: async () => {
      const res = await fetch("/api/chat/history")
      if (!res.ok) return []
      const data = await res.json()
      return Array.isArray(data?.messages) ? (data.messages as Message[]) : []
    },
    initialData: [
      {
        role: "assistant",
        content: "Hi, I'm Saarthi. Tell me what's going on.",
      },
    ],
  })

  const sendMessageMutation = useMutation<void, Error, { text: string; agents: string[] }>({
    onMutate: async ({ text, agents }) => {
      await queryClient.cancelQueries({ queryKey: ["messages"] })
      const previousMessages = queryClient.getQueryData<Message[]>(["messages"]) ?? []

      const userMessage: Message = { role: "user", content: text, agents }
      const assistantPlaceholder: Message = { role: "assistant", content: "" }
      queryClient.setQueryData<Message[]>(["messages"], [...previousMessages, userMessage, assistantPlaceholder])
      setStreamingAgents(agents)
    },
    mutationFn: async ({ text, agents }) => {
      const history = queryClient.getQueryData<Message[]>(["messages"]) ?? []
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: text,
          messages: history.map((m) => ({ role: m.role, content: m.content })),
          activeAgents: agents,
          user_id: USER_ID,
        }),
      })

      if (!res.ok) throw new Error("Streaming request failed")

      if (!res.body) {
        const fallback = await res.text()
        queryClient.setQueryData<Message[]>(["messages"], (current = []) => {
          if (current.length === 0) return current
          const copy = [...current]
          const last = copy[copy.length - 1]
          if (last.role === "assistant") copy[copy.length - 1] = { ...last, content: fallback || "Done." }
          return copy
        })
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let assistantText = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        assistantText += decoder.decode(value, { stream: true })

        queryClient.setQueryData<Message[]>(["messages"], (current = []) => {
          if (current.length === 0) return current
          const copy = [...current]
          const last = copy[copy.length - 1]
          if (last.role === "assistant") {
            copy[copy.length - 1] = { ...last, content: assistantText }
          }
          return copy
        })
      }
    },
    onError: () => {
      queryClient.setQueryData<Message[]>(["messages"], (current = []) => {
        if (current.length === 0) return current
        const copy = [...current]
        const last = copy[copy.length - 1]
        if (last.role === "assistant") {
          copy[copy.length - 1] = { ...last, content: "Streaming failed. Please try again." }
        }
        return copy
      })
    },
    onSettled: () => {
      setStreamingAgents([])
    },
  })

  async function sendMessage(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const text = input.trim()
    if (!text || sendMessageMutation.isPending) return

    setInput("")
    await sendMessageMutation.mutateAsync({ text, agents: selectedAgents })
  }

  return (
    <div className="flex h-full min-h-[70vh] flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <MorningBriefing />
        <ChatFeed messages={messages} isStreaming={sendMessageMutation.isPending} streamingAgents={streamingAgents} />
      </div>

      <form onSubmit={sendMessage} className="border-t border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Send a mission request..."
            className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || sendMessageMutation.isPending}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {sendMessageMutation.isPending ? "Streaming..." : "Send"}
          </button>
        </div>
      </form>
    </div>
  )
}

export type { StreamingChatPanelProps }
