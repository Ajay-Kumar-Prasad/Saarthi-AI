import { proxyPost } from "@/app/api/_lib/proxy";

const USER_ID = "00000000-0000-0000-0000-000000000001";

export async function GET() {
  return proxyPost(
    "/proactive/morning-briefing",
    { user_id: USER_ID, days: 7 },
    "orchestrator",
  );
}
