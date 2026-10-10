import styles from "./range-bar.module.css";

export interface RangeBarProps {
  min: number;
  p25: number;
  median: number;
  p75: number;
  max: number;
  format?: (value: number) => string;
  ariaLabel?: string;
}

const defaultFormat = (value: number) => new Intl.NumberFormat("en-US").format(value);

export function RangeBar({ min, p25, median, p75, max, format = defaultFormat, ariaLabel }: RangeBarProps) {
  const span = max - min;
  const at = (value: number) => (span > 0 ? Math.min(100, Math.max(0, ((value - min) / span) * 100)) : 0);
  const stats: Array<[string, number]> = [
    ["Min", min],
    ["P25", p25],
    ["Median", median],
    ["P75", p75],
    ["Max", max],
  ];
  return (
    <figure className={styles.figure} aria-label={ariaLabel}>
      <div className={styles.line} aria-hidden="true">
        <span className={styles.band} style={{ left: `${at(p25)}%`, width: `${at(p75) - at(p25)}%` }} />
        <span className={styles.end} style={{ left: "0%" }} />
        <span className={styles.end} style={{ left: "100%" }} />
        <span className={styles.median} style={{ left: `${at(median)}%` }} />
      </div>
      <dl className={styles.stats}>
        {stats.map(([label, value]) => (
          <div key={label} className={styles.stat}>
            <dt>{label}</dt>
            <dd>{format(value)}</dd>
          </div>
        ))}
      </dl>
    </figure>
  );
}
