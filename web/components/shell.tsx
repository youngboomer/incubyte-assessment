import type { ReactNode } from "react";
import { logoutAction } from "../lib/auth-actions";

export function Shell({ children }: { children: ReactNode }) {
  return (
    <>
      <header>
        <strong>CompPulse</strong>
        <nav>
          <a href="/">Dashboard</a>
          <a href="/employees">Employees</a>
          <a href="/settings/fx">FX rates</a>
          <form action={logoutAction}>
            <button type="submit">Logout</button>
          </form>
        </nav>
      </header>
      <main>{children}</main>
    </>
  );
}
