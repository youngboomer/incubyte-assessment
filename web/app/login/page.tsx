import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { backendFetch } from "../../lib/api";
import { SESSION_COOKIE } from "../../lib/session";
import { LoginForm } from "./login-form";
import styles from "./login.module.css";

export const metadata = { title: "Sign in | CompPulse" };

export default async function LoginPage() {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (token) {
    let status: number | null = null;
    try {
      status = (await backendFetch("/auth/me", token)).status;
    } catch {
      status = null;
    }
    if (status !== null && status >= 200 && status < 300) {
      redirect("/");
    }
    if (status === 401) {
      redirect("/logout");
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        <div className={styles.brand}>
          <h1>CompPulse</h1>
          <p>Salary management for HR</p>
        </div>
        <LoginForm />
        <p className={styles.footer}>Salary data is confidential.</p>
      </div>
    </main>
  );
}
