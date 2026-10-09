"use client";

import { useActionState } from "react";
import { loginAction, type LoginState } from "../../lib/auth-actions";

const initialState: LoginState = { error: "" };

export function LoginForm() {
  const [state, formAction, pending] = useActionState(loginAction, initialState);

  return (
    <form action={formAction}>
      <label>
        Email
        <input name="email" type="email" autoComplete="username" required />
      </label>
      <label>
        Password
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
      </label>
      <button type="submit" disabled={pending}>
        Log in
      </button>
      {state.error ? <p>{state.error}</p> : null}
    </form>
  );
}
