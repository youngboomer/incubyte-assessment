"use client";

import { useId, useState, type ReactNode } from "react";
import { ChevronDownIcon, SearchIcon } from "../icons";
import { Button } from "./button";
import { cx } from "./cx";
import styles from "./filter-bar.module.css";

export interface FilterBarProps {
  search?: { name: string; defaultValue?: string; label?: string; placeholder?: string };
  activeCount?: number;
  action?: string;
  hidden?: Record<string, string>;
  submitLabel?: string;
  children?: ReactNode;
  chips?: ReactNode;
}

export function FilterBar({
  search,
  activeCount = 0,
  action,
  hidden,
  submitLabel = "Apply",
  children,
  chips,
}: FilterBarProps) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const searchId = useId();
  const label = search?.label ?? "Search";

  return (
    <div className={styles.bar}>
      <form method="get" action={action} role="search" className={styles.form}>
        {Object.entries(hidden ?? {}).map(([key, value]) => (
          <input key={key} type="hidden" name={key} value={value} />
        ))}
        <div className={styles.top}>
          {search ? (
            <div className={styles.search}>
              <label htmlFor={searchId} className="sr-only">
                {label}
              </label>
              <span className={styles.searchIcon}>
                <SearchIcon size={16} />
              </span>
              <input
                id={searchId}
                type="search"
                name={search.name}
                defaultValue={search.defaultValue}
                placeholder={search.placeholder ?? `${label}…`}
                className={styles.searchInput}
              />
            </div>
          ) : null}
          {children ? (
            <button
              type="button"
              className={styles.toggle}
              aria-expanded={open}
              aria-controls={panelId}
              onClick={() => setOpen((value) => !value)}
            >
              Filters
              {activeCount > 0 ? (
                <span className={styles.badge}>
                  {activeCount}
                  <span className="sr-only"> active</span>
                </span>
              ) : null}
              <ChevronDownIcon size={16} className={cx(styles.caret, open && styles.caretOpen)} />
            </button>
          ) : null}
        </div>
        {children ? (
          <div id={panelId} className={cx(styles.panel, open && styles.panelOpen)}>
            <div className={styles.fields}>{children}</div>
          </div>
        ) : null}
        <Button type="submit" size="sm" className={styles.submit}>
          {submitLabel}
        </Button>
      </form>
      {chips ? <div className={styles.chips}>{chips}</div> : null}
    </div>
  );
}
