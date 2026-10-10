import type { ReactNode } from "react";
import { CheckIcon, InfoIcon, WarningIcon } from "../icons";
import { cx } from "./cx";
import styles from "./notice.module.css";

export type NoticeTone = "info" | "warning" | "error" | "success";

export interface NoticeProps {
  tone?: NoticeTone;
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function Notice({ tone = "info", title, children, action, className }: NoticeProps) {
  const role = tone === "error" || tone === "warning" ? "alert" : "status";
  return (
    <div role={role} className={cx(styles.notice, styles[tone], className)}>
      <span className={styles.icon}>
        {tone === "success" ? <CheckIcon /> : tone === "info" ? <InfoIcon /> : <WarningIcon />}
      </span>
      <div className={styles.body}>
        {title ? <p className={styles.title}>{title}</p> : null}
        {children ? <div className={styles.text}>{children}</div> : null}
      </div>
      {action ? <div className={styles.action}>{action}</div> : null}
    </div>
  );
}
