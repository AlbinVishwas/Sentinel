/**
 * Frontend-owned session: the browser holds an httpOnly cookie this app sets;
 * the FastAPI backend only mints/verifies the JWT inside it. Route handlers read
 * the cookie and forward it to the backend as `Authorization: Bearer <jwt>`.
 */
export const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export const SESSION_COOKIE = "sentinel_session";
export const OAUTH_STATE_COOKIE = "sentinel_oauth_state";

const isProd = process.env.NODE_ENV === "production";

/** httpOnly cookie options shared by the session and short-lived OAuth-state cookies. */
export function cookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    secure: isProd, // Secure only in prod so local http dev still works
    sameSite: "lax" as const,
    path: "/",
    maxAge: maxAgeSeconds,
  };
}
