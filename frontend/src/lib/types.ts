/** Stream event shapes emitted by the backend `/agent/stream` SSE endpoint.
 *  Mirrors sentinel_agent/runner.py:stream_agent. */
export type AgentEvent =
  | { type: "reasoning"; text: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string }
  | { type: "final"; text: string }
  | { type: "aborted"; message: string }
  | { type: "error"; message: string }
  | { type: "done" };

/** A single rendered turn in the conversation. */
export type ChatMessage = {
  id: string;
  role: "user" | "agent";
  text: string;
};

/** One entry in the agency log (the visible record of what the agent did). */
export type AgencyEntry =
  | { kind: "reasoning"; text: string }
  | { kind: "tool_call"; name: string; args: Record<string, unknown> }
  | { kind: "tool_result"; name: string }
  | { kind: "status"; text: string; tone: "working" | "success" | "danger" };
