import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { backendFetch } from "../../lib/api";
import { SESSION_COOKIE } from "../../lib/session";
import { LoginForm } from "./login-form";

export default async function LoginPage() {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (token) {
    try {
      const me = await backendFetch("/auth/me", token);
      if (me.ok) {
        redirect("/");
      }
      if (me.status === 401) {
        redirect("/logout");
      }
    } catch {
      // Show the form when the backend cannot be reached.
    }
  }

  return (
    <main>
      <h1>CompPulse</h1>
      <LoginForm />
    </main>
  );
}
