import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { logout } from "../../lib/endpoints";
import { SESSION_COOKIE, clearedSessionCookieOptions } from "../../lib/session";

async function clearSession(): Promise<NextResponse> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (token) {
    await logout(token).catch(() => undefined);
  }
  // Relative Location keeps the browser on the public host. request.url is the
  // internal origin, which would send a proxied demo to localhost.
  const response = new NextResponse(null, {
    status: 307,
    headers: { location: "/login" },
  });
  response.cookies.set(SESSION_COOKIE, "", clearedSessionCookieOptions);
  return response;
}

export const dynamic = "force-dynamic";

export function GET(): Promise<NextResponse> {
  return clearSession();
}

export function POST(): Promise<NextResponse> {
  return clearSession();
}
