import { NextResponse } from "next/server"

export async function GET() {
  return NextResponse.json({
    messages: [
      {
        role: "assistant",
        content: "Hi, I'm Saarthi. Tell me what's going on.",
      },
    ],
  })
}
