import { NextResponse } from "next/server"
import { fallbackAgentResponse, isAgentResponse } from "@/types/agent"

const BACKEND = process.env.BACKEND_URL ?? process.env.API_URL ?? "http://localhost:8080"

export async function DELETE() {
  try {
    const res = await fetch(`${BACKEND}/user/delete`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    })
    const payload = (await res.json().catch(() => null)) as unknown
    if (!isAgentResponse(payload)) {
      return NextResponse.json(
        fallbackAgentResponse("privacy_agent", "Backend returned invalid response format."),
        { status: 502 },
      )
    }
    return NextResponse.json(payload, { status: res.ok ? 200 : res.status })
  } catch (error) {
    return NextResponse.json(
      fallbackAgentResponse(
        "privacy_agent",
        error instanceof Error ? `Delete request failed: ${error.message}` : "Delete request failed.",
      ),
      { status: 502 },
    )
  }
}
