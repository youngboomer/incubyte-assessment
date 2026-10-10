"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { login } from "../../lib/endpoints";
import { SESSION_COOKIE, sessionCookieOptions } from "../../lib/session";

export type SignInState = {
  error: string;
  email: string;
};

export async function signInAction(_state: SignInState, formData: FormData): Promise<SignInState> {
  const rawEmail = formData.get("email");
  const rawPassword = formData.get("password");
  const email = typeof rawEmail === "string" ? rawEmail.trim() : "";
  const password = typeof rawPassword === "string" ? rawPassword : "";
  if (email === "" || password === "") {
    return { error: "Enter your email and password.", email };
  }

  const result = await login({ email, password });
  if (!result.ok) {
    return { error: result.message, email };
  }
  if (!result.data.access_token) {
    return { error: "Something went wrong. Try again.", email };
  }

  (await cookies()).set(SESSION_COOKIE, result.data.access_token, sessionCookieOptions);
  redirect("/");
}
