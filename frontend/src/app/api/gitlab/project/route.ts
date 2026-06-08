const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const path = searchParams.get("path") ?? "";

  const upstream = await fetch(
    `${BACKEND_URL}/gitlab/project?path=${encodeURIComponent(path)}`,
  ).catch(() => null);

  if (!upstream || !upstream.ok) {
    return Response.json({ ok: false, reason: "unreachable" });
  }

  const data = await upstream.json();
  return Response.json(data);
}
