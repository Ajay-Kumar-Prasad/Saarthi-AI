import { proxyGet } from "@/app/api/_lib/proxy";

export async function GET() {
  return proxyGet("/finance/summary", "finance_agent");
}