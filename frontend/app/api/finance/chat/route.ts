import { NextRequest, NextResponse } from "next/server";
 
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8080";
 
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${BACKEND}/agent/finance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ reply: "⚠ Backend unreachable." }, { status: 502 });
  }
}