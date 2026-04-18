import { NextResponse } from "next/server"
import { AgentResponse } from "@/types/agent"

export async function GET() {
  const response: AgentResponse<Record<string, unknown>> = {
    agent: "chat_history",
    status: "ok",
    summary: "Chat history loaded.",
    conflicts: [],
    actions_taken: [],
    data: {
      messages: [
        {
          role: "assistant",
          content: "Hi, I'm Saarthi. Tell me what's going on.",
        },
      ],
    },
  }
  return NextResponse.json(response)
}
