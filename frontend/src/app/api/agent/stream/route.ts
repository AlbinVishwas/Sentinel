/**
 * Proxy route: browser -> this handler -> FastAPI `/agent/stream`.
 *
 * Keeping the backend behind a same-origin route handler means the browser never
 * sees the backend URL or any token, there is no CORS in production, and the SSE
 * body is piped straight through unbuffered.
 */
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const body = await req.text();

  const upstream = await fetch(`${BACKEND_URL}/agent/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(
      `data: ${JSON.stringify({
        type: "error",
        message: `Backend unavailable (${upstream.status}).`,
      })}\n\ndata: ${JSON.stringify({ type: "done" })}\n\n`,
      { status: 200, headers: { "Content-Type": "text/event-stream" } },
    );
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
