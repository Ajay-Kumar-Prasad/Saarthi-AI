import { AgentStatus } from "@/types/agent";

const styles: Record<AgentStatus, string> = {
  ok: "bg-emerald-100 text-emerald-700 border-emerald-200",
  partial: "bg-amber-100 text-amber-700 border-amber-200",
  error: "bg-rose-100 text-rose-700 border-rose-200",
};

export default function AgentStatusBadge({ status }: { status: AgentStatus }) {
  return (
    <span className={`inline-flex rounded-full border px-2 py-1 text-xs font-medium ${styles[status]}`}>
      {status.toUpperCase()}
    </span>
  );
}
