"use client"
import { useEffect, useState } from "react"
import Header from "@/components/shared/Header"
import StatusCards from "@/components/learning/StatusCards"
import ResourceList from "@/components/learning/ResourceList"
import SkillGap from "@/components/learning/SkillGap"
import FlashcardReview from "@/components/learning/FlashcardReview"
import LearningPath from "@/components/learning/LearningPath"
import ChatBox from "@/components/learning/ChatBox"
import { api, type LearningStatus } from "@/lib/api"

export default function LearningPage() {
  const [status, setStatus] = useState<LearningStatus | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    api.learning.status()
      .then(setStatus)
      .catch(() => setError("Could not reach Learning Agent. Is the API running?"))
  }, [])

  return (
    <>
      <Header title="Learning" subtitle="Your study dashboard · powered by Learning Agent" />
      <div className="p-8 space-y-6">
        {error && (
          <div className="bg-red-950 border border-red-800 text-red-400 text-sm rounded-xl px-4 py-3">
            {error}
          </div>
        )}

        {status && <StatusCards data={status} />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {status && (
              <div>
                <h2 className="text-white font-medium mb-3 text-sm">In Progress</h2>
                <ResourceList resources={status.resources} />
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
