// frontend/app/api/finance/expenses/route.ts
// Returns paginated expense list from backend
 
import { NextRequest, NextResponse } from "next/server";
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8080";
 
export async function GET(req: NextRequest) {
  try {
    const res = await fetch(`${BACKEND}/finance/expenses`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ expenses: [] }, { status: 502 });
  }
}