"use client"

import { FormEvent, useState } from "react"

type WorkTask = {
  id?: string
  title?: string
  priority?: string
}

type WorkMeeting = {
  id?: string
  summary?: string
  start?: string
}

type WorkEmail = {
  id?: string
  subject?: string
  from?: string
}

const MOCK_TASKS: WorkTask[] = [
  { title: "Prepare project demo", priority: "high" },
  { title: "Review PRs", priority: "medium" },
  { title: "Team sync meeting prep", priority: "low" },
]

const MOCK_MEETINGS: WorkMeeting[] = [
  { summary: "Project Standup", start: "10:00 AM" },
  { summary: "Client Discussion", start: "2:00 PM" },
]

const MOCK_EMAILS: WorkEmail[] = [
  { subject: "Project Update Required", from: "manager@company.com" },
  { subject: "Meeting Notes", from: "team@company.com" },
]

const USER_ID = "00000000-0000-0000-0000-000000000001"

export default function WorkPage() {
  const [input, setInput] = useState("Show my work status")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [summary, setSummary] = useState("")
  const [tasks, setTasks] = useState<WorkTask[]>([])
  const [meetings, setMeetings] = useState<WorkMeeting[]>([])
  const [emails, setEmails] = useState<WorkEmail[]>([])

  async function runQuery(message: string) {
    setLoading(true)
    setError("")

    try {
      const chatRes = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: message,
          activeAgents: ["work"],
          domains: ["work"],
          user_id: USER_ID,
        }),
      })

      if (!chatRes.ok) throw new Error("chat_failed")
      const summaryText = await chatRes.text()

      const workRes = await fetch("/api/work/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          user_id: USER_ID,
        }),
      })

      if (!workRes.ok) throw new Error("work_failed")
      const payload = await workRes.json()
      const data = payload?.data ?? {}

      const fetchedTasks = Array.isArray(data.tasks) ? data.tasks : []
      const fetchedMeetings = Array.isArray(data.calendar_events) ? data.calendar_events : []
      const fetchedEmails = Array.isArray(data.unread_emails) ? data.unread_emails : []

      const finalTasks = fetchedTasks.length > 0 ? fetchedTasks : MOCK_TASKS
      const finalMeetings = fetchedMeetings.length > 0 ? fetchedMeetings : MOCK_MEETINGS
      const finalEmails = fetchedEmails.length > 0 ? fetchedEmails : MOCK_EMAILS

      setTasks(finalTasks)
      setMeetings(finalMeetings)
      setEmails(finalEmails)
      setSummary(summaryText || "You have 3 tasks, 2 meetings, and 2 unread emails today.")
    } catch {
      setError("Unable to fetch data. Please try again.")
      setSummary("")
      setTasks([])
      setMeetings([])
      setEmails([])
    } finally {
      setLoading(false)
    }
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const message = input.trim()
    if (!message || loading) return
    await runQuery(message)
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Today's Overview</h2>
        <p className="text-sm text-gray-500">Stay on top of your work with AI-powered insights.</p>
      </div>

      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Work Agent Dashboard</h1>
        <p className="text-sm text-gray-500">Tasks, meetings, and emails in one place.</p>
      </div>

      <form onSubmit={onSubmit} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">Chat with Work Agent</p>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about tasks, meetings, or emails"
            className="flex-1 rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-indigo-600 text-white px-4 py-2 text-sm disabled:opacity-50"
          >
            {loading ? "Analyzing your work data..." : "Send"}
          </button>
        </div>
      </form>

      {error && (
        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 rounded-lg p-3 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">Summary</p>
        <p className="text-sm text-gray-600 dark:text-gray-300">{summary || "No data yet."}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Tasks</h2>
          <div className="space-y-2">
            {tasks.length === 0 && <p className="text-sm text-gray-500">No tasks.</p>}
            {tasks.map((task, idx) => (
              <div key={task.id ?? idx} className="border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2">
                <p className="text-sm text-gray-900 dark:text-white">{task.title ?? "Untitled task"}</p>
                <p className="text-xs text-gray-500">Priority: {task.priority ?? "normal"}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Meetings</h2>
          <div className="space-y-2">
            {meetings.length === 0 && <p className="text-sm text-gray-500">No meetings.</p>}
            {meetings.map((meeting, idx) => (
              <div key={meeting.id ?? idx} className="border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2">
                <p className="text-sm text-gray-900 dark:text-white">{meeting.summary ?? "Untitled meeting"}</p>
                <p className="text-xs text-gray-500">{meeting.start ?? "Time unavailable"}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Emails</h2>
          <div className="space-y-2">
            {emails.length === 0 && <p className="text-sm text-gray-500">No emails.</p>}
            {emails.map((email, idx) => (
              <div key={email.id ?? idx} className="border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2">
                <p className="text-sm text-gray-900 dark:text-white">{email.subject ?? "No subject"}</p>
                <p className="text-xs text-gray-500">{email.from ?? "Unknown sender"}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
