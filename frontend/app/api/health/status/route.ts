import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"
import { proxyPost } from "@/app/api/_lib/proxy"

export async function POST(req: NextRequest) {
  const cookieStore = await cookies()
  console.log("cookies",cookieStore)
  const cookieUserId = cookieStore.get("health_user_id")?.value
  console.log("cookies user id",cookieUserId)
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>
  const userId =
    typeof body.user_id === "string" && body.user_id.trim()
      ? body.user_id.trim()
      : cookieUserId

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

  return proxyPost("/health/status", { ...body, user_id: userId }, "health_agent")
}
