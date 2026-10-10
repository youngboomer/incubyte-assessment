import type { ReactNode } from "react";
import styles from "./timeline.module.css";

export interface TimelineItem {
  id: string;
  date: ReactNode;
  title: ReactNode;
  details?: ReactNode;
}

export function Timeline({ items, ariaLabel }: { items: TimelineItem[]; ariaLabel?: string }) {
  return (
    <ol className={styles.list} aria-label={ariaLabel}>
      {items.map((item) => (
        <li key={item.id} className={styles.item}>
          <span className={styles.dot} aria-hidden="true" />
          <div className={styles.body}>
            <p className={styles.date}>{item.date}</p>
            <p className={styles.title}>{item.title}</p>
            {item.details ? <div className={styles.details}>{item.details}</div> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
