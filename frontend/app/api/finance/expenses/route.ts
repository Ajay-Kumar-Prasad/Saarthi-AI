import { proxyGet } from "@/app/api/_lib/proxy";

export async function GET() {
  return proxyGet("/finance/expenses", "finance_agent");
}