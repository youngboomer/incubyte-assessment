import { Shell } from "../../components/shell";
import { PageHeader, Skeleton, SkeletonRows } from "../../components/ui";
import styles from "./employees.module.css";

export default function LoadingEmployees() {
  return (
    <Shell>
      <PageHeader title="Employees" />
      <div className={styles.loadingBar}>
        <Skeleton height="44px" />
      </div>
      <div className={styles.loadingRows}>
        <SkeletonRows rows={8} label="Loading employees" />
      </div>
    </Shell>
  );
}
