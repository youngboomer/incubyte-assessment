"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { CloseIcon, HistoryIcon, MenuIcon, PaymentsIcon, PeopleIcon, TuneIcon } from "./icons";
import { NAV_ITEMS, type NavIcon } from "./nav-items";
import styles from "./shell.module.css";

const ICONS: Record<NavIcon, () => ReactNode> = {
  people: () => <PeopleIcon />,
  payments: () => <PaymentsIcon />,
  tune: () => <TuneIcon />,
  history: () => <HistoryIcon />,
};

function isActive(pathname: string, href: string, exact?: boolean) {
  if (exact || href === "/") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function ShellNav({ signOut }: { signOut: ReactNode }) {
  const pathname = usePathname();
  const [openFor, setOpenFor] = useState<string | null>(null);
  const open = openFor === pathname;
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpenFor(null);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <aside className={styles.side} data-open={open}>
      <div className={styles.bar}>
        <Link href="/employees" className={styles.brand}>
          <span className={styles.mark} aria-hidden="true">
            C
          </span>
          <span>CompPulse</span>
        </Link>
        <button
          ref={buttonRef}
          type="button"
          className={styles.menuButton}
          aria-expanded={open}
          aria-controls="primary-nav"
          onClick={() => setOpenFor(open ? null : pathname)}
        >
          {open ? <CloseIcon /> : <MenuIcon />}
          <span>Menu</span>
        </button>
      </div>
      <div id="primary-nav" className={styles.panel}>
        <nav aria-label="Primary">
          <ul className={styles.list}>
            {NAV_ITEMS.map((item) => {
              const active = isActive(pathname, item.href, item.exact);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={styles.link}
                    aria-current={active ? "page" : undefined}
                  >
                    {ICONS[item.icon]()}
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className={styles.bottom}>{signOut}</div>
      </div>
    </aside>
  );
}
