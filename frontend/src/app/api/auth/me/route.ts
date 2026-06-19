/**
 * Who is signed in? Read the session cookie, forward it to the backend as a
 * bearer, and return the user's public profile. Backs the client-side auth gate.
 */
import { cookies } from "next/headers";
import { BACKEND_URL, SESSION_COOKIE } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (!token) {
    return Response.json({ authenticated: false }, { status: 401 });
  }

  const res = await fetch(`${BACKEND_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => null);

  if (!res || !res.ok) {
    return Response.json({ authenticated: false }, { status: 401 });
  }

  const user = await res.json();
  return Response.json({ authenticated: true, user });
}
