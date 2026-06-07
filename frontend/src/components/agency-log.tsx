import type { AgencyEntry } from "@/lib/types";

type Status = "idle" | "working" | "done" | "aborted" | "error";

interface AgencyLogProps {
  entries: AgencyEntry[];
  status?: Status;
}

export function AgencyLog({ entries, status }: AgencyLogProps) {
  if (entries.length === 0) return null;

  return (
    <div className="mb-4 rounded border border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="border-b border-[var(--color-border)] px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-[var(--color-faint)] flex items-center justify-between">
        <span>Execution Telemetry Logs</span>
        {status === "working" && (
          <span className="flex items-center gap-1.5 font-mono text-[9px] text-[var(--color-muted)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-text)] pulse-indicator"></span>
            Streaming
          </span>
        )}
      </div>
      <div className="relative p-4 flex flex-col gap-4">
        {/* Timeline connector path line */}
        {entries.length > 1 && (
          <div className="absolute left-[25px] top-[24px] bottom-[24px] w-[1px] bg-[var(--color-border)]" />
        )}
        
        {entries.map((entry, i) => {
          const isLast = i === entries.length - 1;
          const isActive = isLast && status === "working";
          
          return (
            <div key={i} className="relative flex items-start gap-3 text-[12.5px] leading-relaxed">
              {/* Timeline dot with custom SVG icon */}
              <div 
                className={`relative z-10 flex h-[19px] w-[19px] shrink-0 items-center justify-center rounded-full border bg-[var(--color-surface)] transition-colors duration-200 ${
                  isActive 
                    ? "border-[var(--color-text)] ring-1 ring-[var(--color-text)]/20" 
                    : "border-[var(--color-border)]"
                }`}
              >
                <div className={isActive ? "pulse-indicator" : ""}>
                  <AgencyIcon entry={entry} />
                </div>
              </div>
              
              {/* Timeline item content */}
              <div className="flex-1 min-w-0 pt-0.5">
                <AgencyContent entry={entry} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AgencyIcon({ entry }: { entry: AgencyEntry }) {
  switch (entry.kind) {
    case "reasoning":
      return <SparkleIcon />;
    case "tool_call": {
      const name = entry.name.toLowerCase();
      if (name.includes("git") || name.includes("commit") || name.includes("push") || name.includes("branch") || name.includes("merge_request")) {
        return <GitBranchIcon />;
      }
      if (name.includes("grep") || name.includes("search") || name.includes("find") || name.includes("list") || name.includes("read") || name.includes("view")) {
        return <EyeIcon />;
      }
      if (name.includes("edit") || name.includes("write") || name.includes("create") || name.includes("replace") || name.includes("save")) {
        return <CodeIcon />;
      }
      return <TerminalIcon />;
    }
    case "tool_result":
      return <CheckIcon />;
    case "status":
      return <InfoIcon />;
  }
}

function AgencyContent({ entry }: { entry: AgencyEntry }) {
  switch (entry.kind) {
    case "reasoning":
      return (
        <div>
          <span className="font-mono text-[9px] uppercase tracking-widest text-[var(--color-faint)] block mb-0.5">
            Reasoning Process
          </span>
          <span className="text-[var(--color-muted)] font-sans text-[12.5px] leading-relaxed block">
            {entry.text}
          </span>
        </div>
      );
    case "tool_call": {
      const arg = primaryArg(entry.args);
      return (
        <div>
          <span className="font-mono text-[9px] uppercase tracking-widest text-[var(--color-faint)] block mb-0.5">
            Invoking Tool
          </span>
          <span className="font-mono text-[12.5px] text-[var(--color-text)] block break-all">
            {entry.name}
            {arg ? <span className="text-[var(--color-muted)] font-mono text-[11px]"> ({arg})</span> : null}
          </span>
        </div>
      );
    }
    case "tool_result":
      return (
        <div>
          <span className="font-mono text-[9px] uppercase tracking-widest text-[var(--color-faint)] block mb-0.5">
            Tool Returned
          </span>
          <span className="font-mono text-[12.5px] text-[var(--color-muted)] block">
            Execution completed for <strong className="text-[var(--color-text)] font-semibold">{entry.name}</strong>
          </span>
        </div>
      );
    case "status":
      return (
        <div>
          <span className="font-mono text-[9px] uppercase tracking-widest text-[var(--color-faint)] block mb-0.5">
            Status Update
          </span>
          <span
            className="font-sans text-[12.5px] leading-relaxed block"
            style={{ color: `var(--color-${toneVar(entry.tone)})` }}
          >
            {entry.text}
          </span>
        </div>
      );
  }
}

function SparkleIcon() {
  return (
    <svg className="h-3 w-3 text-[var(--color-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg className="h-3 w-3 text-[var(--color-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg className="h-3 w-3 text-[var(--color-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function GitBranchIcon() {
  return (
    <svg className="h-3 w-3 text-[var(--color-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="6" y1="3" x2="6" y2="15" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <path d="M18 9a9 9 0 0 1-9 9" />
    </svg>
  );
}

function TerminalIcon() {
  return (
    <svg className="h-3 w-3 text-[var(--color-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="h-3 w-3 text-[var(--color-text)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg className="h-3 w-3 text-[var(--color-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
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
