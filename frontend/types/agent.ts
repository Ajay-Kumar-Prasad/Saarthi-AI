export type AgentStatus = "ok" | "partial" | "error";

export type AgentResponse<TData = Record<string, unknown>> = {
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

  const validStatus = ["ok", "partial", "error"];

  return (
    typeof v.agent === "string" &&
    typeof v.status === "string" &&
    validStatus.includes(v.status) &&
    typeof v.summary === "string" &&
    Array.isArray(v.conflicts) &&
    Array.isArray(v.actions_taken) &&
    typeof v.data === "object" &&
    v.data !== null &&
    !Array.isArray(v.data)
  );
}

export function fallbackAgentResponse(agent: string, message: string): AgentResponse {
  return {
    agent,
    status: "error",
    summary: message,
    conflicts: [],
    actions_taken: [],
    data: {},
  };
}