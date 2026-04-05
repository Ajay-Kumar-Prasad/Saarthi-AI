import { cookies } from "next/headers"
import { NextRequest, NextResponse } from "next/server"

// GET /api/health/connect?user_id=xxx
// Redirects the user to the backend Google OAuth URL.
// After Google redirects back, the backend should redirect to /api/health/connect/callback
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const userId = searchParams.get("user_id")

  if (!userId) {
    return NextResponse.json({ error: "user_id is required" }, { status: 400 })
  }

  const backendUrl = `http://127.0.0.1:8000/auth/google/login?user_id=${encodeURIComponent(userId)}`
  return NextResponse.redirect(backendUrl)
}
