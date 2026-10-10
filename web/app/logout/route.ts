import { NextResponse } from "next/server";
import { SESSION_COOKIE, clearedSessionCookieOptions } from "../../lib/session";

function clearSession(): NextResponse {
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

export function GET(): NextResponse {
  return clearSession();
}

export function POST(): NextResponse {
  return clearSession();
}
