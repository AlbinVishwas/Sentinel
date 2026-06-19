/**
 * GitLab redirects the browser here with `?code&state`. We match `state` against
 * the cookie set at /api/auth/login (CSRF), hand the code to the backend to
 * exchange for tokens + a session JWT, then set that JWT as our httpOnly session
 * cookie and bounce the user back into the app.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import {
  BACKEND_URL,
  OAUTH_STATE_COOKIE,
  SESSION_COOKIE,
  cookieOptions,
} from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");

  const jar = await cookies();
  const expectedState = jar.get(OAUTH_STATE_COOKIE)?.value;

  const fail = (reason: string) => {
    const resp = NextResponse.redirect(new URL(`/chat?auth_error=${reason}`, req.url));
    resp.cookies.delete(OAUTH_STATE_COOKIE);
    return resp;
  };

  if (!code || !state || !expectedState || state !== expectedState) {
    return fail("state");
  }

  const res = await fetch(`${BACKEND_URL}/auth/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, state }),
  }).catch(() => null);

  if (!res || !res.ok) {
    return fail("exchange");
  }

  const data = (await res.json()) as { session_token: string; expires_in: number };

  const resp = NextResponse.redirect(new URL("/chat", req.url));
  resp.cookies.set(SESSION_COOKIE, data.session_token, cookieOptions(data.expires_in));
  resp.cookies.delete(OAUTH_STATE_COOKIE);
  return resp;
}
