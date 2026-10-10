import styles from "./histogram.module.css";

export interface HistogramBucket {
  label: string;
  count: number;
}

export interface HistogramProps {
  data: HistogramBucket[];
  ariaLabel: string;
}

const number = new Intl.NumberFormat("en-US");

export function Histogram({ data, ariaLabel }: HistogramProps) {
  const max = Math.max(0, ...data.map((bucket) => bucket.count));
  return (
    <figure className={styles.figure}>
      <div className={styles.plot} aria-hidden="true">
        {data.map((bucket) => {
          const percent = max > 0 ? (bucket.count / max) * 100 : 0;
          return (
            <div key={bucket.label} className={styles.column} title={`${bucket.label}: ${number.format(bucket.count)}`}>
              <span className={styles.count}>{number.format(bucket.count)}</span>
              <span className={styles.slot}>
                <span
                  className={bucket.count === max && max > 0 ? styles.peak : styles.bar}
                  style={{ height: `${percent}%` }}
                />
              </span>
              <span className={styles.label}>{bucket.label}</span>
            </div>
          );
        })}
      </div>
      <table className="sr-only">
        <caption>{ariaLabel}</caption>
        <thead>
          <tr>
            <th scope="col">Range</th>
            <th scope="col">Count</th>
          </tr>
        </thead>
        <tbody>
          {data.map((bucket) => (
            <tr key={bucket.label}>
              <th scope="row">{bucket.label}</th>
              <td>{number.format(bucket.count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
