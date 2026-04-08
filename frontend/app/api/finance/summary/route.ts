// frontend/app/api/finance/summary/route.ts
// Returns category totals for the chart
 
import { NextRequest, NextResponse } from "next/server";
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8080";
export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/finance/summary`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ summary: [] }, { status: 502 });
  }
}