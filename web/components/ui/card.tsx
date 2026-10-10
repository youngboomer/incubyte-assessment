import type { ReactNode } from "react";
import { cx } from "./cx";
import styles from "./card.module.css";

export interface CardProps {
  children: ReactNode;
  padded?: boolean;
  className?: string;
  "aria-label"?: string;
}

export function Card({ children, padded = true, className, ...rest }: CardProps) {
  return (
    <section {...rest} className={cx(styles.card, padded && styles.padded, className)}>
      {children}
    </section>
  );
}

export interface CardHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function CardHeader({ title, description, actions }: CardHeaderProps) {
  return (
    <div className={styles.header}>
      <div className={styles.headerText}>
        <h2 className={styles.title}>{title}</h2>
        {description ? <p className={styles.description}>{description}</p> : null}
      </div>
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </div>
  );
}
