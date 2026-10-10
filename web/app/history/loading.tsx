import { Shell } from "../../components/shell";
import { Skeleton, SkeletonRows } from "../../components/ui";

export default function Loading() {
  return (
    <Shell>
      <Skeleton width="min(100%, 240px)" height="32px" />
      <SkeletonRows rows={8} label="Loading change history" />
    </Shell>
  );
}
