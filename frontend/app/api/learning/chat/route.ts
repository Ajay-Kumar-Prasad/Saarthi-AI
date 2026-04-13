import { NextRequest } from "next/server";
import { proxyPost } from "@/app/api/_lib/proxy";

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  return proxyPost("/learning/chat", body, "learning_agent");
}
