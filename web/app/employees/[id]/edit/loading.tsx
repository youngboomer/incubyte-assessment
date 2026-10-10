import { Shell } from "../../../../components/shell";
import { Card, Skeleton } from "../../../../components/ui";
import styles from "./edit.module.css";

export default function LoadingEdit() {
  return (
    <Shell>
      <div className={styles.page} role="status" aria-busy="true">
        <span className="sr-only">Loading edit form</span>
        <Skeleton width="40%" height="28px" />
        <div className={styles.columns}>
          <Card>
            <Skeleton height="360px" />
          </Card>
          <Card>
            <Skeleton height="240px" />
          </Card>
        </div>
      </div>
    </Shell>
  );
}
