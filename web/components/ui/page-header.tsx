import type { ReactNode } from "react";
import styles from "./page-header.module.css";

export interface PageHeaderProps {
  title: ReactNode;
  count?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  breadcrumb?: ReactNode;
}

export function PageHeader({ title, count, subtitle, actions, breadcrumb }: PageHeaderProps) {
  return (
    <header className={styles.header}>
      {breadcrumb ? <div className={styles.breadcrumb}>{breadcrumb}</div> : null}
      <div className={styles.row}>
        <div className={styles.text}>
          <h1 className={styles.title}>
            {title}
            {count !== undefined && count !== null ? (
              <span className={styles.count}>{count}</span>
            ) : null}
          </h1>
          {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
        </div>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </div>
    </header>
  );
}
