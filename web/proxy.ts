import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { decideProxy } from "./proxy-rules";
import { SESSION_COOKIE } from "./lib/session";

export function proxy(request: NextRequest) {
  const hasToken = Boolean(request.cookies.get(SESSION_COOKIE)?.value);
  const decision = decideProxy(request.nextUrl.pathname, hasToken);
  if (decision === "next") return NextResponse.next();
  if ("rewrite" in decision) return NextResponse.rewrite(new URL(decision.rewrite, request.url));
  return NextResponse.redirect(new URL(decision.redirect, request.url));
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
