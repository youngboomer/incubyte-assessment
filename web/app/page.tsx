import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { Shell } from "../components/shell";
import { backendFetch } from "../lib/api";
import { SESSION_COOKIE } from "../lib/session";
import type { MeResponse } from "../lib/types";

export default async function Page() {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }

  let meResponse: Response;
  try {
    meResponse = await backendFetch("/auth/me", token);
  } catch (error) {
    return (
      <Shell>
        <p>{backendMessage(error)}</p>
      </Shell>
    );
  }

  if (meResponse.status === 401) {
    redirect("/logout");
  }
  if (!meResponse.ok) {
    return (
      <Shell>
        <p>Backend is down</p>
      </Shell>
    );
  }

  const me = (await meResponse.json()) as MeResponse;
  const health = await readHealth();

  return (
    <Shell>
      <p>{me.email}</p>
      <pre>{health}</pre>
    </Shell>
  );
}

async function readHealth(): Promise<string> {
  try {
    const response = await backendFetch("/health");
    if (!response.ok) {
      return "Backend is down";
    }
    const body: unknown = await response.json();
    return JSON.stringify(body);
  } catch (error) {
    return backendMessage(error);
  }
}

function backendMessage(error: unknown): string {
  if (error instanceof Error && error.message === "BACKEND_URL is not set") {
    return "BACKEND_URL is not set";
  }
  return "Backend is down";
}
