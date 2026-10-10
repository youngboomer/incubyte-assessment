import { Shell } from "../../../components/shell";
import { Card, Skeleton } from "../../../components/ui";
import styles from "./profile.module.css";

export default function LoadingEmployee() {
  return (
    <Shell>
      <div className={styles.page} role="status" aria-busy="true">
        <span className="sr-only">Loading employee</span>
        <Skeleton width="min(100%, 320px)" height="28px" />
        <Skeleton width="min(100%, 480px)" height="16px" />
        <div className={styles.cards}>
          <Card>
            <Skeleton width="40%" height="20px" />
            <Skeleton height="120px" className={styles.sub} />
          </Card>
          <Card>
            <Skeleton width="40%" height="20px" />
            <Skeleton height="120px" className={styles.sub} />
          </Card>
        </div>
        <Card>
          <Skeleton height="160px" />
        </Card>
      </div>
    </Shell>
  );
}
