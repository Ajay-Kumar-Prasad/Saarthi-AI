import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

// GET /api/health/connect/callback?user_id=xxx&success=true
// Called after the backend completes the Google OAuth flow.
// Sets cookies to mark the user as connected, then redirects to the health dashboard.
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const userId = searchParams.get("user_id")
  const success = searchParams.get("success")

  if (!userId || success !== "true") {
    return NextResponse.redirect(new URL("/health?error=oauth_failed", request.url))
  }

  const cookieStore = await cookies()
  const oneYear = 60 * 60 * 24 * 365

  cookieStore.set("health_google_connected", "true", {
    httpOnly: true,
    path: "/",
    maxAge: oneYear,
  })
  cookieStore.set("health_user_id", userId, {
    httpOnly: true,
    path: "/",
    maxAge: oneYear,
  })

  // Redirect to health page — the sync will happen automatically on first load
  return NextResponse.redirect(new URL("/health", request.url))
}
