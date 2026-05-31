import type { AgencyEntry } from "@/lib/types";

/**
 * The visible record of the agent's intermediate steps (Quadrant D).
 * Plain monospace lines, appended statically as events arrive — no animation.
 */
export function AgencyLog({ entries }: { entries: AgencyEntry[] }) {
  if (entries.length === 0) return null;

  return (
    <div className="mb-3 rounded-md border border-[var(--color-border)] bg-[var(--color-bg)]">
      <div className="border-b border-[var(--color-border)] px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-[var(--color-faint)]">
        Agent activity
      </div>
      <ul className="px-3 py-2 font-mono text-[12.5px] leading-relaxed">
        {entries.map((entry, i) => (
          <li key={i} className="flex gap-2">
            <AgencyLine entry={entry} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function AgencyLine({ entry }: { entry: AgencyEntry }) {
  switch (entry.kind) {
    case "reasoning":
      return (
        <span className="text-[var(--color-muted)]">
          <span className="text-[var(--color-faint)]">[reasoning]</span> {entry.text}
        </span>
      );
    case "tool_call": {
      const arg = primaryArg(entry.args);
      return (
        <span className="text-[var(--color-text)]">
          <span className="text-[var(--color-accent)]">[MCP call]</span> {entry.name}
          {arg ? <span className="text-[var(--color-muted)]"> {arg}</span> : null}
        </span>
      );
    }
    case "tool_result":
      return (
        <span className="text-[var(--color-muted)]">
          <span className="text-[var(--color-faint)]">[result]</span> {entry.name} returned
        </span>
      );
    case "status":
      return (
        <span
          style={{ color: `var(--color-${toneVar(entry.tone)})` }}
        >
          {entry.text}
        </span>
      );
  }
}

function toneVar(tone: "working" | "success" | "danger") {
  if (tone === "success") return "success";
  if (tone === "danger") return "danger";
  return "accent";
}

/** Show the most meaningful argument inline (project/branch/issue), compactly. */
function primaryArg(args: Record<string, unknown>): string {
  const keys = ["issue_iid", "file_path", "branch", "source_branch", "project_id"];
  for (const k of keys) {
    if (k in args && args[k] != null) return `${k}=${String(args[k])}`;
  }
  const first = Object.keys(args)[0];
  return first ? `${first}=${String(args[first])}` : "";
}
