import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE } from "./lib/session";

export function proxy(request: NextRequest) {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const { pathname } = request.nextUrl;

  const needsLogin =
    pathname === "/" ||
    pathname.startsWith("/employees") ||
    pathname.startsWith("/settings");
  if (pathname === "/" && !token) {
    // Serve the login document at the published URL. A 307 body is only the
    // path, so the health payload would not be in this response.
    return NextResponse.rewrite(new URL("/login", request.url));
  }
  if (needsLogin && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (pathname === "/login" && token) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
