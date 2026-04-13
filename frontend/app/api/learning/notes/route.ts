import { NextRequest } from "next/server"
import { proxyPost } from "@/app/api/_lib/proxy"

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>
  const note = typeof body.note === "string" ? body.note : ""
  const resource = typeof body.resource === "string" ? body.resource : ""

  // If note content is provided — it's a SAVE request
  const message = note
    ? `save this note for ${resource}: ${note}`
    : resource
    ? `show notes for ${resource}`
    : "show my notes"

  return proxyPost("/learning/chat", { ...body, message }, "learning_agent")
}
