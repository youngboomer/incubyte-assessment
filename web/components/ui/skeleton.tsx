import { cx } from "./cx";
import styles from "./skeleton.module.css";

export interface SkeletonProps {
  width?: string;
  height?: string;
  className?: string;
}

export function Skeleton({ width = "100%", height = "16px", className }: SkeletonProps) {
  return <span aria-hidden="true" className={cx(styles.block, className)} style={{ width, height }} />;
}

export function SkeletonRows({ rows = 6, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-busy="true" className={styles.rows}>
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className={styles.row}>
          <Skeleton width="30%" />
          <Skeleton width="20%" />
          <Skeleton width="15%" />
        </div>
      ))}
    </div>
  );
}
