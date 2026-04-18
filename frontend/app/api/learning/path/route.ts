import { NextRequest } from "next/server"
import { proxyPost } from "@/app/api/_lib/proxy"

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>
  const message = typeof body.message === "string" && body.message.trim() ? body.message : "Show my learning path"
  return proxyPost("/learning/chat", { ...body, message }, "learning_agent")
}
