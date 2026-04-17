import { proxyPost } from "@/app/api/_lib/proxy";

const USER_ID = "chjoshna145@gmail.com";

export async function GET() {
  return proxyPost(
    "/proactive/morning-briefing",
    { user_id: USER_ID, days: 7 },
    "orchestrator",
  );
}
