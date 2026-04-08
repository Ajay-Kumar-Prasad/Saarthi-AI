import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  const cookieStore = await cookies()
  const userId = cookieStore.get("health_user_id")?.value

  if (!userId) {
    return NextResponse.json({ error: "Not connected." }, { status: 401 })
  }

  const body = await request.json()

  try {
    const API = process.env.API_URL || "http://localhost:8080"
    const res = await fetch(`${API}/health/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: body.message, user_id: userId }),
      signal: AbortSignal.timeout(30_000),
    })

    if (!res.ok) {
      return NextResponse.json({ error: `Backend error: ${res.status}` }, { status: 502 })
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error"
    return NextResponse.json({ error: "Could not reach health backend.", detail: message }, { status: 503 })
  }
}
