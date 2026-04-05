import { NextRequest, NextResponse } from "next/server"
const API = process.env.API_URL ?? "http://localhost:8080"
export async function POST(req: NextRequest) {
  const body = await req.json()
  const res = await fetch(`${API}/learning/chat`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, message: "What flashcards do I need to review today?" }),
  })
  return NextResponse.json(await res.json())
}
