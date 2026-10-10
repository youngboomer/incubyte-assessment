import Link from "next/link";
import { ChevronRightIcon } from "../icons";
import styles from "./breadcrumb.module.css";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className={styles.nav}>
      <ol className={styles.list}>
        {items.map((item, index) => {
          const last = index === items.length - 1;
          return (
            <li key={`${item.label}-${index}`} className={styles.item}>
              {item.href && !last ? (
                <Link href={item.href} className={styles.link}>
                  {item.label}
                </Link>
              ) : (
                <span aria-current={last ? "page" : undefined} className={styles.current}>
                  {item.label}
                </span>
              )}
              {last ? null : <ChevronRightIcon size={16} className={styles.sep} />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
