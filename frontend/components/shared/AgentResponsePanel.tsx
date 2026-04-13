import AgentStatusBadge from "@/components/shared/AgentStatusBadge";
import { AgentResponse } from "@/types/agent";

export default function AgentResponsePanel({
  response,
  title,
}: {
  response: AgentResponse;
  title: string;
}) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
        <AgentStatusBadge status={response.status} />
      </div>

      <p className="rounded-lg bg-indigo-50 p-3 text-sm text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">
        {response.summary}
      </p>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Conflicts</p>
          {response.conflicts.length === 0 ? (
            <p className="text-sm text-gray-500">No conflicts.</p>
          ) : (
            <ul className="space-y-1">
              {response.conflicts.map((conflict) => (
                <li
                  key={conflict}
                  className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-950/20 dark:text-amber-300"
                >
                  {conflict}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Actions Taken</p>
          {response.actions_taken.length === 0 ? (
            <p className="text-sm text-gray-500">No actions recorded.</p>
          ) : (
            <ul className="space-y-1">
              {response.actions_taken.map((action) => (
                <li key={action} className="rounded-md bg-gray-100 px-2 py-1 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                  {action}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
