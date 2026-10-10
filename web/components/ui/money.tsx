import { cx } from "./cx";
import styles from "./money.module.css";

export interface MoneyProps {
  local: string;
  usd?: string;
  align?: "start" | "end";
}

export function Money({ local, usd, align = "end" }: MoneyProps) {
  return (
    <span className={cx(styles.money, align === "start" && styles.start)}>
      <span className={styles.local}>{local}</span>
      {usd ? <span className={styles.usd}>{usd}</span> : null}
    </span>
  );
}
