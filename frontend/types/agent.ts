export type AgentStatus = "ok" | "partial" | "error";

export type AgentResponse<TData = Record<string, unknown> | null> = {
  agent: string;
  status: AgentStatus;
  summary: string;
  conflicts: string[];
  actions_taken: string[];
  data: TData;
};

export function isAgentResponse(value: unknown): value is AgentResponse {
  if (!value || typeof value !== "object") return false;
  const v = value as Partial<AgentResponse>;
  return (
    typeof v.agent === "string" &&
    typeof v.status === "string" &&
    typeof v.summary === "string" &&
    Array.isArray(v.conflicts) &&
    Array.isArray(v.actions_taken) &&
    "data" in v
  );
}

export function fallbackAgentResponse(agent: string, message: string): AgentResponse {
  return {
    agent,
    status: "error",
    summary: message,
    conflicts: [],
    actions_taken: [],
    data: null,
  };
}
