import { NextResponse } from "next/server";
import { SESSION_COOKIE, sessionCookieOptions } from "../../lib/session";

function clearSession(): NextResponse {
  // Relative Location keeps the browser on the public host. request.url is the
  // internal origin, which would send a proxied demo to localhost.
  const response = new NextResponse(null, {
    status: 307,
    headers: { location: "/login" },
  });
  response.cookies.set(SESSION_COOKIE, "", {
    ...sessionCookieOptions,
    maxAge: 0,
  });
  return response;
}

export const dynamic = "force-dynamic";

export function GET(): NextResponse {
  return clearSession();
}

export function POST(): NextResponse {
  return clearSession();
}
