import { cookies } from "next/headers";
import { BACKEND_URL, SESSION_COOKIE } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const path = searchParams.get("path") ?? "";

  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return Response.json({ ok: false, reason: "unauthorized" });
  }

  const upstream = await fetch(
    `${BACKEND_URL}/gitlab/project?path=${encodeURIComponent(path)}`,
    { headers: { Authorization: `Bearer ${token}` } },
  ).catch(() => null);

  if (!upstream || !upstream.ok) {
    return Response.json({ ok: false, reason: "unreachable" });
  }

  const data = await upstream.json();
  return Response.json(data);
}
