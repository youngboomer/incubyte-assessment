import { connection } from "next/server";

export default async function Page() {
  const health = await readHealth();

  return (
    <main>
      <h1>CompPulse</h1>
      <p>{health}</p>
    </main>
  );
}

async function readHealth(): Promise<string> {
  // Dynamic lookup stays runtime. A static process.env.BACKEND_URL is inlined at build.
  await connection();
  const backendUrl = process.env["BACKEND_URL"];
  if (!backendUrl) {
    return "BACKEND_URL is not set";
  }

  try {
    const response = await fetch(`${backendUrl}/health`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return "Backend is down";
    }
    const body: unknown = await response.json();
    return JSON.stringify(body);
  } catch {
    return "Backend is down";
  }
}
