import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

// POST /api/health/sync
// Calls the backend /health/status to sync and return the latest health data.
// Also updates the health_last_sync cookie to today's date so we only sync once per day.
export async function POST(request: NextRequest) {
  const cookieStore = await cookies()
  const userId = cookieStore.get("health_user_id")?.value

  if (!userId) {
    return NextResponse.json({ error: "Not connected. Complete Google Fit OAuth first." }, { status: 401 })
  }

  const body = await request.json().catch(() => ({}))
  const days = body.days ?? 30

  try {
    const res = await fetch("http://127.0.0.1:8000/health/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, days }),
      signal: AbortSignal.timeout(30_000),
    })

    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json({ error: `Backend error: ${res.status}`, detail: text }, { status: 502 })
    }

    const data = await res.json()

    // Mark last sync as today
    cookieStore.set("health_last_sync", new Date().toISOString().slice(0, 10), {
      httpOnly: true,
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    })

    return NextResponse.json(data)
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error"
    return NextResponse.json({ error: "Could not reach health backend.", detail: message }, { status: 503 })
  }
}
