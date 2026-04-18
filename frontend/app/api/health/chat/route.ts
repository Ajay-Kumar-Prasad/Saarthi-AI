import { cookies } from "next/headers"
import { NextResponse } from "next/server"
import { NextRequest } from "next/server"
import { proxyPost } from "@/app/api/_lib/proxy"

export async function POST(request: NextRequest) {
  const cookieStore = await cookies()
  const userId = cookieStore.get("health_user_id")?.value

  if (!userId) {
    return NextResponse.json(
      {
        agent: "health_agent",
        status: "error",
        summary: "Google Fit is not connected for this session.",
        conflicts: [],
        actions_taken: [],
        data: null,
      },
      { status: 401 },
    )
  }

  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>
  const message = typeof body.message === "string" ? body.message : ""
  return proxyPost("/health/chat", { message, user_id: userId }, "health_agent")
}
