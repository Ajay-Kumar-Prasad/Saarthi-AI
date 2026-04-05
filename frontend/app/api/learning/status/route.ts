import { NextRequest, NextResponse } from "next/server"
const API = process.env.API_URL ?? "http://localhost:8080"
export async function POST(req: NextRequest) {
  const body = await req.json()
  const res = await fetch(`${API}/learning/status`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return NextResponse.json(await res.json())
}
