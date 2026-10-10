"use client";

import { Button, Notice } from "../../../../components/ui";
import type { StaleInfo } from "./server";
import styles from "./shared.module.css";

export function StaleNotice({
  info,
  reloadLabel,
}: {
  info: StaleInfo | null;
  reloadLabel: string;
}) {
  const yourView = info
    ? [`version ${info.yourVersion}`, info.yourLabel].filter(Boolean).join(", ")
    : null;
  const now = info
    ? [
        `version ${info.nowVersion}`,
        info.nowLabel,
        info.changedBy ? `changed by ${info.changedBy}` : null,
        info.reason ? `reason: ${info.reason}` : null,
      ]
        .filter(Boolean)
        .join(", ")
    : null;
  return (
    <Notice
      tone="warning"
      title="Someone else changed this record while you were editing. Nothing was saved."
      action={
        <Button variant="quiet" size="sm" onClick={() => window.location.reload()}>
          {reloadLabel}
        </Button>
      }
    >
      {info ? (
        <dl className={styles.compare}>
          <dt>Your view:</dt>
          <dd>{yourView}</dd>
          <dt>Now:</dt>
          <dd>{now}</dd>
        </dl>
      ) : null}
    </Notice>
  );
}
