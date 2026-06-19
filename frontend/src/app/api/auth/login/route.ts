/**
 * Begin GitLab OAuth. Ask the backend for the authorize URL + CSRF state, stash
 * the state in a short-lived httpOnly cookie (so the value GitLab echoes back can
 * be matched to this browser), then redirect the browser to GitLab.
 */
import { NextResponse } from "next/server";
import { BACKEND_URL, OAUTH_STATE_COOKIE, cookieOptions } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const res = await fetch(`${BACKEND_URL}/auth/login`).catch(() => null);
  if (!res || !res.ok) {
    return NextResponse.redirect(new URL("/chat?auth_error=login_unavailable", req.url));
  }

  const { authorize_url, state } = (await res.json()) as {
    authorize_url: string;
    state: string;
  };

  const resp = NextResponse.redirect(authorize_url);
  resp.cookies.set(OAUTH_STATE_COOKIE, state, cookieOptions(10 * 60)); // 10 min
  return resp;
}
