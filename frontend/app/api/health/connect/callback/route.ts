import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

// GET /api/health/connect/callback?user_id=xxx&success=true
// Called after the backend completes the Google OAuth flow.
// Sets cookies to mark the user as connected, then redirects to the health dashboard.
export async function GET(request: NextRequest) {
  const appUrl = (
    process.env.FRONTEND_URL ??
    process.env.NEXT_PUBLIC_APP_URL ??
    process.env.APP_URL ??
    ""
  ).replace(/\/$/, "")
  const { searchParams } = new URL(request.url)
  const userId = searchParams.get("user_id")
  const success = searchParams.get("success")

  if (!userId || success !== "true") {
    const target = appUrl
      ? `${appUrl}/health?error=oauth_failed`
      : new URL("/health?error=oauth_failed", request.url)
    return NextResponse.redirect(target)
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
  const target = appUrl ? `${appUrl}/health` : new URL("/health", request.url)
  return NextResponse.redirect(target)
}