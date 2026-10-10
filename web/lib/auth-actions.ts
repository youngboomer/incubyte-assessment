"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { backendFetch } from "./api";
import { logout } from "./endpoints";
import { SESSION_COOKIE, clearedSessionCookieOptions, sessionCookieOptions } from "./session";
import type { LoginResponse } from "./types";

export type LoginState = {
  error: string;
};

export async function loginAction(
  _state: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const email = formData.get("email");
  const password = formData.get("password");
  if (typeof email !== "string" || typeof password !== "string") {
    return { error: "Invalid credentials" };
  }

  let response: Response;
  try {
    response = await backendFetch("/auth/login", undefined, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    return { error: "Invalid credentials" };
  }

  if (!response.ok) {
    return { error: "Invalid credentials" };
  }

  let body: LoginResponse;
  try {
    body = (await response.json()) as LoginResponse;
  } catch {
    return { error: "Invalid credentials" };
  }
  if (!body.access_token) {
    return { error: "Invalid credentials" };
  }

  const jar = await cookies();
  jar.set(SESSION_COOKIE, body.access_token, sessionCookieOptions);
  redirect("/");
}

export async function logoutAction(): Promise<void> {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (token) {
    await logout(token).catch(() => undefined);
  }
  jar.set(SESSION_COOKIE, "", clearedSessionCookieOptions);
  redirect("/login");
}
