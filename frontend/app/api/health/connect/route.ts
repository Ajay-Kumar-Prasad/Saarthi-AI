import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const userId = searchParams.get("user_id")

  if (!userId) {
    return NextResponse.json({ error: "user_id is required" }, { status: 400 })
  }

  const API = process.env.API_URL || "http://localhost:8080"
  const backendUrl = `${API}/auth/google/login?user_id=${encodeURIComponent(userId)}`
  return NextResponse.redirect(backendUrl)
}
