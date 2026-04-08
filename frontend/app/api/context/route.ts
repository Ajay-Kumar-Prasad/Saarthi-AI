import { NextRequest, NextResponse } from "next/server"

type ContextAgent = "work" | "health" | "finance" | "learning" | "social"

export async function GET(req: NextRequest) {
  const agent = (req.nextUrl.searchParams.get("agent") ?? "learning").toLowerCase() as ContextAgent

  const contextByAgent = {
    finance: {
      financeData: [
        { month: "Jan", Spend: 42000 },
        { month: "Feb", Spend: 38500 },
        { month: "Mar", Spend: 45100 },
        { month: "Apr", Spend: 39800 },
      ],
    },
    health: {
      sleepData: [
        { day: "Mon", SleepHours: 6.5 },
        { day: "Tue", SleepHours: 7.2 },
        { day: "Wed", SleepHours: 5.9 },
        { day: "Thu", SleepHours: 6.8 },
        { day: "Fri", SleepHours: 7.4 },
        { day: "Sat", SleepHours: 8.0 },
        { day: "Sun", SleepHours: 7.1 },
      ],
    },
    work: {
      tasks: {
        total: 18,
        dueToday: 5,
        blocked: 2,
        completed: 11,
      },
    },
    learning: {},
    social: {},
  } as const

  return NextResponse.json({
    agent,
    context: contextByAgent[agent] ?? contextByAgent.learning,
  })
}
