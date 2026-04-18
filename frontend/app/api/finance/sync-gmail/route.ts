import { proxyPost } from "@/app/api/_lib/proxy";

export async function POST() {
  return proxyPost("/sync-gmail", {}, "finance_agent");
}
