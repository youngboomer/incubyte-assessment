export type ProxyDecision = "next" | { redirect: string } | { rewrite: string };

const PUBLIC_PATHS = ["/login", "/logout"];

export function decideProxy(pathname: string, hasToken: boolean): ProxyDecision {
  if (pathname === "/login") return hasToken ? { redirect: "/" } : "next";
  if (PUBLIC_PATHS.includes(pathname) || hasToken) return "next";
  return pathname === "/" ? { rewrite: "/login" } : { redirect: "/login" };
}
