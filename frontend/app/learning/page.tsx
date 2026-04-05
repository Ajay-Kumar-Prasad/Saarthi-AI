import Header from "@/components/shared/Header"
import ResourceList from "@/components/learning/ResourceList"
import UpcomingSessions from "@/components/learning/UpcomingSessions"
import StatusCards from "@/components/learning/StatusCards"
import SkillGap from "@/components/learning/SkillGap"
import FlashcardReview from "@/components/learning/FlashcardReview"
import LearningPath from "@/components/learning/LearningPath"
import ChatBox from "@/components/learning/ChatBox"
import type { LearningStatus } from "@/lib/api"

async function getStatus(): Promise<LearningStatus | null> {
  try {
    const res = await fetch("http://localhost:8080/learning/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "00000000-0000-0000-0000-000000000001" }),
      cache: "no-store",
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function LearningPage() {
  const status = await getStatus()

  return (
    <>
      <Header title="Learning" subtitle="Your study dashboard · powered by Learning Agent" />
      <div className="p-8 space-y-6">

        {!status && (
          <div className="bg-red-950 border border-red-800 text-red-400 text-sm rounded-xl px-4 py-3">
            Could not reach Learning Agent on port 8080. Run ./start.sh first.
          </div>
        )}

        {status && <StatusCards data={status} />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">

            {status && status.resources.length > 0 && (
              <div>
                <p className="text-gray-400 text-xs uppercase tracking-wide mb-3">In Progress</p>
                <ResourceList resources={status.resources} />
              </div>
            )}

            {status && status.upcoming_sessions.length > 0 && (
              <div>
                <p className="text-gray-400 text-xs uppercase tracking-wide mb-3">Upcoming Sessions</p>
                <UpcomingSessions sessions={status.upcoming_sessions} />
              </div>
            )}

            <LearningPath />
            <SkillGap />
          </div>

          <div className="space-y-6">
            <FlashcardReview />
            <ChatBox />
          </div>
        </div>
      </div>
    </>
  )
}
