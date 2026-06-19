/**
 * Proxy route: browser -> this handler -> FastAPI `/agent/stream`.
 *
 * Keeping the backend behind a same-origin route handler means the browser never
 * sees the backend URL or any token, there is no CORS in production, and the SSE
 * body is piped straight through unbuffered.
 */
import { cookies } from "next/headers";
import { BACKEND_URL, SESSION_COOKIE } from "@/lib/auth";

export const dynamic = "force-dynamic";

const sse = (event: object) =>
  new Response(
    `data: ${JSON.stringify(event)}\n\ndata: ${JSON.stringify({ type: "done" })}\n\n`,
    { status: 200, headers: { "Content-Type": "text/event-stream" } },
  );

export async function POST(req: Request) {
  const body = await req.text();

  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return sse({ type: "error", message: "Not connected to GitLab. Please connect first." });
  }

  const upstream = await fetch(`${BACKEND_URL}/agent/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body,
  });

  if (upstream.status === 401) {
    return sse({ type: "error", message: "GitLab connection expired. Please reconnect." });
  }

  if (!upstream.ok || !upstream.body) {
    return sse({ type: "error", message: `Backend unavailable (${upstream.status}).` });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
