import { cx } from "./cx";
import styles from "./status-tag.module.css";

export type EmployeeStatus = "Active" | "Terminated";

export function StatusTag({ status }: { status: EmployeeStatus }) {
  return (
    <span className={cx(styles.tag, status === "Terminated" ? styles.terminated : styles.active)}>
      {status}
    </span>
  );
}
