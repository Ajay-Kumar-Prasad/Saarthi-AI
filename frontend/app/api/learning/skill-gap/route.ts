import { NextRequest } from "next/server"
import { proxyPost } from "@/app/api/_lib/proxy"

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>
  const role = typeof body.role === "string" && body.role.trim() ? body.role : "Data Engineer"
  return proxyPost(
    "/learning/chat",
    { ...body, message: `What skills am I missing to become a ${role}?` },
    "learning_agent",
  )
}
