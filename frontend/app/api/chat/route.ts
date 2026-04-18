import { NextRequest } from "next/server"
import { fallbackAgentResponse, isAgentResponse } from "@/types/agent"

const API = process.env.BACKEND_URL ?? process.env.API_URL ?? "http://localhost:8080"

type ChatRequestBody = {
  prompt?: string
  messages?: Array<{ role: string; content: string }>
  activeAgents?: string[]
  active_agents?: string[]
  user_id?: string
}

function getLatestUserPrompt(body: ChatRequestBody): string {
  if (body.prompt && body.prompt.trim()) return body.prompt.trim()
  const latest = [...(body.messages ?? [])].reverse().find((m) => m.role === "user")
  return latest?.content?.trim() ?? ""
}

function toTokenStream(text: string) {
  const encoder = new TextEncoder()
  const tokens = text.split(/(\s+)/).filter((token) => token.length > 0)

  return new ReadableStream<Uint8Array>({
    start(controller) {
      let index = 0

      function pushNext() {
        if (index >= tokens.length) {
          controller.close()
          return
        }

        controller.enqueue(encoder.encode(tokens[index]))
        index += 1
        setTimeout(pushNext, 18)
      }

      pushNext()
    },
  })
}

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as ChatRequestBody
  const prompt = getLatestUserPrompt(body)
  const activeAgents = body.activeAgents ?? body.active_agents ?? []
  const domains = activeAgents.map((agent) => agent.toLowerCase())

  if (!prompt) {
    return new Response("", {
      status: 200,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
      },
    })
  }

  try {
    const response = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: body.user_id ?? "chjoshna145@gmail.com",
        message: prompt,
        domains,
      }),
    })

    if (!response.ok) {
      return new Response("Streaming request failed", { status: response.status })
    }

    const payload = (await response.json()) as unknown
    const safePayload = isAgentResponse(payload)
      ? payload
      : fallbackAgentResponse("orchestrator", "Backend returned invalid response format.")
    const assistantText = String(safePayload.summary ?? "Done.")

    return new Response(toTokenStream(assistantText), {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Saarthi-Agents": JSON.stringify(activeAgents.length > 0 ? activeAgents : ["learning"]),
      },
    })
  } catch {
    return new Response("Streaming request failed", { status: 502 })
  }
}
