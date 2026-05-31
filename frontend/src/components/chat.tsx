"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AgencyLog } from "@/components/agency-log";
import type { AgencyEntry, AgentEvent } from "@/lib/types";

type Status = "idle" | "working" | "done" | "aborted" | "error";

type Turn =
  | { role: "user"; id: string; text: string }
  | { role: "agent"; id: string; agency: AgencyEntry[]; text: string; status: Status };

const SUGGESTIONS = [
  "Check open issue #1 and identify the file responsible.",
  "Fix the syntax error in utils/parser.py from issue #1.",
];

export function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Keep the latest content in view. Auto-scroll only; no smooth-scroll animation.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns]);

  const send = useCallback(
    async (prompt: string) => {
      const text = prompt.trim();
      if (!text || busy) return;

      const userTurn: Turn = { role: "user", id: crypto.randomUUID(), text };
      const agentId = crypto.randomUUID();
      const agentTurn: Turn = {
        role: "agent",
        id: agentId,
        agency: [],
        text: "",
        status: "working",
      };
      setTurns((prev) => [...prev, userTurn, agentTurn]);
      setInput("");
      setBusy(true);

      const patch = (fn: (t: Extract<Turn, { role: "agent" }>) => void) =>
        setTurns((prev) =>
          prev.map((t) => {
            if (t.id !== agentId || t.role !== "agent") return t;
            const next = { ...t, agency: [...t.agency] };
            fn(next);
            return next;
          }),
        );

      try {
        const res = await fetch("/api/agent/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text, session_id: "ui" }),
        });
        if (!res.body) throw new Error("no stream");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const line = frame.split("\n").find((l) => l.startsWith("data:"));
            if (!line) continue;
            const event = JSON.parse(line.slice(5).trim()) as AgentEvent;
            applyEvent(event, patch);
          }
        }
      } catch {
        patch((t) => {
          t.status = "error";
          t.agency.push({ kind: "status", text: "Connection failed.", tone: "danger" });
        });
      } finally {
        setBusy(false);
      }
    },
    [busy],
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  };

  return (
    <div className="flex h-screen flex-col">
      <Header />

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 py-8">
          {turns.length === 0 ? (
            <EmptyState onPick={(s) => void send(s)} disabled={busy} />
          ) : (
            <div className="flex flex-col gap-6">
              {turns.map((turn) =>
                turn.role === "user" ? (
                  <UserMessage key={turn.id} text={turn.text} />
                ) : (
                  <AgentMessage key={turn.id} turn={turn} />
                ),
              )}
            </div>
          )}
        </div>
      </div>

      <footer className="border-t border-[var(--color-border)] bg-[var(--color-bg)]">
        <form onSubmit={onSubmit} className="mx-auto w-full max-w-3xl px-4 py-4">
          <div className="flex items-end gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 focus-within:border-[var(--color-accent)]">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
              placeholder="Ask Sentinel to investigate or fix an issue…"
              className="max-h-40 min-h-6 flex-1 resize-none bg-transparent text-[15px] text-[var(--color-text)] placeholder:text-[var(--color-faint)] focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy || input.trim().length === 0}
              className="shrink-0 rounded-md border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1.5 text-sm text-[var(--color-text)] disabled:cursor-not-allowed disabled:text-[var(--color-faint)]"
            >
              {busy ? "Working…" : "Send"}
            </button>
          </div>
          <p className="mt-2 px-1 font-mono text-[11px] text-[var(--color-faint)]">
            Read-write, guardrailed · pushes to main/master/production are blocked · branches confined to sentinel/*
          </p>
        </form>
      </footer>
    </div>
  );
}

function applyEvent(
  event: AgentEvent,
  patch: (fn: (t: Extract<Turn, { role: "agent" }>) => void) => void,
) {
  switch (event.type) {
    case "reasoning":
      patch((t) => t.agency.push({ kind: "reasoning", text: event.text }));
      break;
    case "tool_call":
      patch((t) => t.agency.push({ kind: "tool_call", name: event.name, args: event.args }));
      break;
    case "tool_result":
      patch((t) => t.agency.push({ kind: "tool_result", name: event.name }));
      break;
    case "final":
      patch((t) => {
        t.text = event.text;
        if (t.status === "working") t.status = "done";
      });
      break;
    case "aborted":
      patch((t) => {
        t.status = "aborted";
        t.text = event.message;
        t.agency.push({ kind: "status", text: event.message, tone: "danger" });
      });
      break;
    case "error":
      patch((t) => {
        t.status = "error";
        t.text = event.message;
        t.agency.push({ kind: "status", text: event.message, tone: "danger" });
      });
      break;
    case "done":
      patch((t) => {
        if (t.status === "working") t.status = "done";
      });
      break;
  }
}

function Header() {
  return (
    <header className="flex shrink-0 items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
      <div className="flex items-baseline gap-2">
        <span className="text-sm font-semibold tracking-tight text-[var(--color-text)]">
          Sentinel
        </span>
        <span className="font-mono text-[11px] text-[var(--color-faint)]">
          SRE agent · GitLab
        </span>
      </div>
      <span className="font-mono text-[11px] text-[var(--color-muted)]">
        gemini-3.5-flash
      </span>
    </header>
  );
}

function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (s: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="mt-24 flex flex-col items-center text-center">
      <h1 className="text-lg font-medium text-[var(--color-text)]">
        Autonomous SRE for GitLab
      </h1>
      <p className="mt-2 max-w-md text-sm text-[var(--color-muted)]">
        Sentinel investigates issues, reads repository code, and opens verified fix
        Merge Requests — keeping you in the loop.
      </p>
      <div className="mt-8 flex w-full max-w-md flex-col gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            disabled={disabled}
            className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-left text-sm text-[var(--color-muted)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] disabled:cursor-not-allowed"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function UserMessage({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2 text-[15px] text-[var(--color-text)]">
        {text}
      </div>
    </div>
  );
}

function AgentMessage({ turn }: { turn: Extract<Turn, { role: "agent" }> }) {
  const showWorking = turn.status === "working" && turn.text.length === 0;
  return (
    <div className="flex flex-col">
      <AgencyLog entries={turn.agency} />
      {turn.text ? (
        <div className="whitespace-pre-wrap text-[15px] leading-relaxed text-[var(--color-text)]">
          {turn.text}
        </div>
      ) : showWorking ? (
        <div className="font-mono text-[12.5px] text-[var(--color-muted)]">Working…</div>
      ) : null}
    </div>
  );
}
