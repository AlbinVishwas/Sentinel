/**
 * Sign out — purely a frontend concern: clear the session cookie. The backend
 * session JWT is stateless, so there is nothing server-side to revoke.
 */
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function POST() {
  const resp = NextResponse.json({ ok: true });
  resp.cookies.delete(SESSION_COOKIE);
  return resp;
}
