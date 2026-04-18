"use client"
import { useEffect, useState } from "react"
import Header from "@/components/shared/Header"
import ResourceList from "@/components/learning/ResourceList"
import UpcomingSessions from "@/components/learning/UpcomingSessions"
import StatusCards from "@/components/learning/StatusCards"
import SkillGap from "@/components/learning/SkillGap"
import FlashcardReview from "@/components/learning/FlashcardReview"
import LearningPath from "@/components/learning/LearningPath"
import ChatBox from "@/components/learning/ChatBox"
import StudyGoals from "@/components/learning/StudyGoals"
import StudyNotes from "@/components/learning/StudyNotes"
import AgentResponsePanel from "@/components/shared/AgentResponsePanel"
import { fetchLearningStatus, LearningStatus } from "@/lib/api"
import { AgentResponse } from "@/types/agent"

const USER_ID = "chjoshna145@gmail.com"

export default function LearningPage() {
  const [status, setStatus] = useState<LearningStatus | null>(null)
  const [agentResponse, setAgentResponse] = useState<AgentResponse | null>(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)

  async function fetchStatus() {
    try {
      const response = await fetchLearningStatus(USER_ID)
      setAgentResponse(response)
      setStatus(response.data)
      setError(response.status === "error")
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Refresh every 60s so streak/hours stay live
    const t = setInterval(fetchStatus, 60_000)
    return () => clearInterval(t)
  }, [])

  return (
    <>
      <Header title="Learning" subtitle="Your study dashboard · powered by Learning Agent" />
      <div className="p-8 space-y-6">

        {loading && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="border border-gray-200 dark:border-gray-800 rounded-xl p-5 animate-pulse bg-gray-100 dark:bg-gray-800 h-24" />
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="bg-red-950 border border-red-800 text-red-400 text-sm rounded-xl px-4 py-3">
            Could not reach Learning Agent on port 8080. Run ./start.sh first.
          </div>
        )}

        {status && <StatusCards data={status} />}
        {agentResponse && <AgentResponsePanel title="Learning Agent" response={agentResponse} />}

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

            <StudyGoals initialGoals={status?.active_goals ?? []} />
            <StudyNotes resources={status?.resources ?? []} />
            <LearningPath />
            <SkillGap />

          </div>

          <div className="space-y-6">
            <FlashcardReview />
            <ChatBox onAction={fetchStatus} />
          </div>
        </div>
      </div>
    </>
  )
}