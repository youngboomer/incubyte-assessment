import Link from "next/link";
import { ChevronLeftIcon, ChevronRightIcon } from "../icons";
import { Button } from "./button";
import { cx } from "./cx";
import styles from "./pagination.module.css";

export interface PageSizeControl {
  name: string;
  value: number;
  options: readonly number[];
  hidden?: Record<string, string>;
}

export interface PaginationProps {
  from: number;
  to: number;
  total: number;
  previousHref?: string | null;
  nextHref?: string | null;
  pageSize?: PageSizeControl;
}

const number = new Intl.NumberFormat("en-US");

function Step({ href, direction }: { href?: string | null; direction: "previous" | "next" }) {
  const previous = direction === "previous";
  const content = (
    <>
      {previous ? <ChevronLeftIcon size={16} /> : null}
      {previous ? "Previous" : "Next"}
      {previous ? null : <ChevronRightIcon size={16} />}
    </>
  );
  return href ? (
    <Link href={href} className={styles.step} rel={previous ? "prev" : "next"}>
      {content}
    </Link>
  ) : (
    <span className={cx(styles.step, styles.disabled)} aria-disabled="true">
      {content}
    </span>
  );
}

export function Pagination({ from, to, total, previousHref, nextHref, pageSize }: PaginationProps) {
  const summary =
    total === 0 ? "No results" : `Showing ${number.format(from)}–${number.format(to)} of ${number.format(total)}`;
  return (
    <nav aria-label="Pagination" className={styles.nav}>
      <p className={styles.summary} aria-live="polite">
        {summary}
      </p>
      <div className={styles.controls}>
        {pageSize ? (
          <form method="get" className={styles.size}>
            {Object.entries(pageSize.hidden ?? {}).map(([key, value]) => (
              <input key={key} type="hidden" name={key} value={value} />
            ))}
            <label htmlFor={`${pageSize.name}-select`} className={styles.sizeLabel}>
              Rows per page
            </label>
            <select id={`${pageSize.name}-select`} name={pageSize.name} defaultValue={pageSize.value} className={styles.sizeSelect}>
              {pageSize.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <Button type="submit" variant="quiet" size="sm">
              Apply
            </Button>
          </form>
        ) : null}
        <div className={styles.steps}>
          <Step href={previousHref} direction="previous" />
          <Step href={nextHref} direction="next" />
        </div>
      </div>
    </nav>
  );
}
