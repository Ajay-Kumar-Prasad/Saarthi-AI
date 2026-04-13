import { NextResponse } from "next/server"
import { fallbackAgentResponse, isAgentResponse } from "@/types/agent"

const BACKEND = process.env.BACKEND_URL ?? process.env.API_URL ?? "http://localhost:8080"

function toAgentResponse(payload: unknown, agent: string) {
  if (isAgentResponse(payload)) return payload
  if (payload && typeof payload === "object") {
    const raw = payload as { detail?: unknown; error_type?: unknown }
    if (typeof raw.detail === "string") {
      const mapped = fallbackAgentResponse(agent, raw.detail)
      return {
        ...mapped,
        conflicts:
          typeof raw.error_type === "string" ? [raw.error_type] : mapped.conflicts,
      }
    }
  }
  return null
}

export async function proxyPost(
  backendPath: string,
  body: Record<string, unknown>,
  agent = "proxy",
): Promise<NextResponse> {
  try {
    const res = await fetch(`${BACKEND}${backendPath}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = (await res.json()) as unknown;
    const safePayload = toAgentResponse(payload, agent)
    if (!safePayload) {
      return NextResponse.json(fallbackAgentResponse(agent, "Backend returned invalid response format."), {
        status: 502,
      })
    }
    return NextResponse.json(safePayload, { status: res.ok ? 200 : res.status })
  } catch (error) {
    return NextResponse.json(
      fallbackAgentResponse(
        agent,
        error instanceof Error ? `Backend request failed: ${error.message}` : "Backend request failed.",
      ),
      { status: 502 },
    )
  }
}

export async function proxyGet(
  backendPath: string,
  agent = "proxy",
): Promise<NextResponse> {
  try {
    const res = await fetch(`${BACKEND}${backendPath}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    const payload = (await res.json()) as unknown;
    const safePayload = toAgentResponse(payload, agent)
    if (!safePayload) {
      return NextResponse.json(fallbackAgentResponse(agent, "Backend returned invalid response format."), {
        status: 502,
      })
    }
    return NextResponse.json(safePayload, { status: res.ok ? 200 : res.status })
  } catch (error) {
    return NextResponse.json(
      fallbackAgentResponse(
        agent,
        error instanceof Error ? `Backend request failed: ${error.message}` : "Backend request failed.",
      ),
      { status: 502 },
    )
  }
}
