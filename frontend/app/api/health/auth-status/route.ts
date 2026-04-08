import { cookies } from "next/headers"
import { NextResponse } from "next/server"

// GET /api/health/auth-status
// Returns whether the user has completed Google Fit OAuth consent.
// We track this with an HTTP-only cookie set after the OAuth redirect completes.
export async function GET() {
  const cookieStore = await cookies()
  const connected = cookieStore.get("health_google_connected")?.value === "true"
  const userId = cookieStore.get("health_user_id")?.value ?? null
  const lastSync = cookieStore.get("health_last_sync")?.value ?? null

  return NextResponse.json({ connected, userId, lastSync })
}
