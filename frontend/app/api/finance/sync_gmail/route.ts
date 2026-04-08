// frontend/app/api/finance/sync-gmail/route.ts
 
import { NextRequest, NextResponse } from "next/server";
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8080";
export async function POST() {
  try {
    const res = await fetch(`${BACKEND}/sync-gmail`, { method: "POST" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ message: "Sync failed" }, { status: 502 });
  }
}
 