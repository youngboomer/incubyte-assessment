import styles from "./bar-list.module.css";

export interface BarListItem {
  label: string;
  value: number;
  display: string;
}

export function BarList({ items, ariaLabel }: { items: BarListItem[]; ariaLabel?: string }) {
  const max = Math.max(0, ...items.map((item) => item.value));
  return (
    <ul className={styles.list} aria-label={ariaLabel}>
      {items.map((item) => {
        const percent = max > 0 ? Math.max(0, (item.value / max) * 100) : 0;
        return (
          <li key={item.label} className={styles.row}>
            <span className={styles.label}>{item.label}</span>
            <span className={styles.track} aria-hidden="true">
              <span className={styles.bar} style={{ width: `${percent}%` }} />
            </span>
            <span className={styles.value}>{item.display}</span>
          </li>
        );
      })}
    </ul>
  );
}
