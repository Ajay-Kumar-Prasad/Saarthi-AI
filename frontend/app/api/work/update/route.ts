import { NextRequest } from "next/server";
import { proxyPost } from "@/app/api/_lib/proxy";
export async function POST(req: NextRequest) {
  const body = await req.json();
  return proxyPost("/work/tasks/update", body, "work_agent");
}