import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import { ArrowDownIcon, ArrowUpIcon } from "../icons";
import { cx } from "./cx";
import styles from "./data-table.module.css";

export interface DataTableProps {
  caption: string;
  children: ReactNode;
  className?: string;
}

export function DataTable({ caption, children, className }: DataTableProps) {
  return (
    <div className={cx(styles.wrap, className)}>
      <table className={styles.table}>
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export interface ThProps extends Omit<ComponentProps<"th">, "align"> {
  numeric?: boolean;
}

export function Th({ numeric = false, className, scope = "col", ...rest }: ThProps) {
  return <th {...rest} scope={scope} className={cx(numeric && styles.numeric, className)} />;
}

export interface TdProps extends Omit<ComponentProps<"td">, "align"> {
  label: string;
  numeric?: boolean;
  primary?: boolean;
}

export function Td({ label, numeric = false, primary = false, className, ...rest }: TdProps) {
  return (
    <td
      {...rest}
      data-label={label}
      className={cx(numeric && styles.numeric, primary && styles.primary, className)}
    />
  );
}

export type SortDirection = "asc" | "desc";

export interface SortHeaderProps {
  href: string;
  direction?: SortDirection | null;
  numeric?: boolean;
  children: ReactNode;
}

export function SortHeader({ href, direction = null, numeric = false, children }: SortHeaderProps) {
  const ariaSort = direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none";
  return (
    <th scope="col" aria-sort={ariaSort} className={cx(styles.sortable, numeric && styles.numeric)}>
      <Link href={href} className={cx(styles.sortLink, direction && styles.sorted)} scroll={false}>
        {children}
        <span className={styles.arrow}>
          {direction === "asc" ? <ArrowUpIcon size={16} /> : null}
          {direction === "desc" ? <ArrowDownIcon size={16} /> : null}
        </span>
      </Link>
    </th>
  );
}
