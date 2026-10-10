import type { ReactNode } from "react";
import { logoutAction } from "../lib/auth-actions";
import { LogoutIcon } from "./icons";
import { ShellNav } from "./shell-nav";
import styles from "./shell.module.css";

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.frame}>
      <ShellNav
        signOut={
          <form action={logoutAction} className={styles.signOutForm}>
            <button type="submit" className={styles.signOut}>
              <LogoutIcon />
              Sign out
            </button>
          </form>
        }
      />
      <main className={styles.main}>
        <div className={styles.content}>{children}</div>
      </main>
    </div>
  );
}
