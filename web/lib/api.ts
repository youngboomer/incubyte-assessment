import { headers as nextHeaders } from "next/headers";
import { connection } from "next/server";
import { pickClientIp } from "./client-ip";

export async function backendFetch(
  path: string,
  token?: string,
  init?: RequestInit,
): Promise<Response> {
  if (typeof window !== "undefined") {
    throw new Error("backendFetch does not run in the browser");
  }
  // Dynamic lookup stays runtime. A static process.env.BACKEND_URL is inlined at build.
  await connection();
  const backendUrl = process.env["BACKEND_URL"];
  if (!backendUrl) {
    throw new Error("BACKEND_URL is not set");
  }

  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }
  headers.delete("x-forwarded-for");
  try {
    const clientIp = pickClientIp(await nextHeaders());
    if (clientIp) {
      headers.set("x-forwarded-for", clientIp);
    }
  } catch {
    // outside a request scope there is no visitor address
  }
  const base = backendUrl.replace(/\/$/, "");
  return fetch(`${base}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
}
