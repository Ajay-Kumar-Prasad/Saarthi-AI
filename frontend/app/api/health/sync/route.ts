import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"
import { proxyPost } from "@/app/api/_lib/proxy"

export async function POST(request: NextRequest) {
  const cookieStore = await cookies()
  const userId = cookieStore.get("health_user_id")?.value

  if (!userId) {
    return NextResponse.json(
      {
        agent: "health_agent",
        status: "error",
        summary: "Not connected. Complete Google Fit OAuth first.",
        conflicts: [],
        actions_taken: [],
        data: null,
      },
      { status: 401 },
    )
  }

  const body = await request.json().catch(() => ({}))
  const days = body.days ?? 30

  const response = await proxyPost("/health/sync", { user_id: userId, days }, "health_agent")

  if (response.status === 200) {
    cookieStore.set("health_last_sync", new Date().toISOString().slice(0, 10), {
      httpOnly: true,
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    })
  }
  return response
}
