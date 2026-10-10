"use client";

import { useActionState, useState } from "react";
import { Button, Input, Notice } from "../../components/ui";
import { signInAction, type SignInState } from "./actions";
import styles from "./login.module.css";

const initialState: SignInState = { error: "", email: "" };

export function LoginForm() {
  const [state, formAction, pending] = useActionState(signInAction, initialState);
  const [visible, setVisible] = useState(false);

  return (
    <form action={formAction} className={styles.form}>
      {state.error ? <Notice tone="error">{state.error}</Notice> : null}
      <Input
        name="email"
        label="Email"
        type="email"
        autoComplete="username"
        defaultValue={state.email}
        key={state.email}
        required
      />
      <div className={styles.passwordRow}>
        <Input
          name="password"
          label="Password"
          type={visible ? "text" : "password"}
          autoComplete="current-password"
          required
        />
        <button
          type="button"
          className={styles.toggle}
          aria-pressed={visible}
          onClick={() => setVisible((value) => !value)}
        >
          {visible ? "Hide" : "Show"}
          <span className="sr-only"> password</span>
        </button>
      </div>
      <Button type="submit" loading={pending} className={styles.submit}>
        Sign in
      </Button>
    </form>
  );
}
