import { NextRequest, NextResponse } from "next/server"

const API = process.env.API_URL ?? "http://localhost:8080"

export async function POST(req: NextRequest) {
  const body = await req.json()

  // If note content is provided — it's a SAVE request
  const message = body.note
    ? `save this note for ${body.resource}: ${body.note}`
    : body.resource
    ? `show notes for ${body.resource}`
    : "show my notes"

  const res = await fetch(`${API}/learning/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, message }),
  })
  return NextResponse.json(await res.json())
}
