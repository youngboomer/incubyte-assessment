import { Shell } from "../components/shell";
import { Skeleton } from "../components/ui";
import styles from "./dashboard.module.css";

export default function Loading() {
  return (
    <Shell>
      <div className={styles.page} role="status" aria-busy="true">
        <span className="sr-only">Loading pay overview</span>
        <Skeleton width="min(100%, 220px)" height="32px" />
        <Skeleton width="min(100%, 360px)" />
        <div className={styles.figures}>
          {[0, 1, 2, 3].map((key) => (
            <div key={key} className={styles.skeletonCard}>
              <Skeleton width="50%" />
              <Skeleton width="70%" height="28px" />
            </div>
          ))}
        </div>
        <div className={styles.skeletonCard}>
          <Skeleton width="40%" />
          <Skeleton height="48px" />
        </div>
        <div className={styles.skeletonCard}>
          <Skeleton width="30%" />
          <Skeleton height="160px" />
        </div>
      </div>
    </Shell>
  );
}
