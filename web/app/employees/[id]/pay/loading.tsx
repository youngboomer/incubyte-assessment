import { Shell } from "../../../../components/shell";
import { Card, Skeleton } from "../../../../components/ui";
import styles from "./pay.module.css";

export default function LoadingPay() {
  return (
    <Shell>
      <div className={styles.narrow} role="status" aria-busy="true">
        <span className="sr-only">Loading pay form</span>
        <Skeleton width="50%" height="28px" />
        <Card>
          <Skeleton height="80px" />
        </Card>
        <Card>
          <Skeleton height="260px" />
        </Card>
      </div>
    </Shell>
  );
}
