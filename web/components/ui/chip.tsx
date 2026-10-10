import Link from "next/link";
import { CloseIcon } from "../icons";
import styles from "./chip.module.css";

export interface ChipProps {
  label: string;
  removeHref: string;
}

export function Chip({ label, removeHref }: ChipProps) {
  return (
    <li className={styles.chip}>
      <span>{label}</span>
      <Link href={removeHref} className={styles.remove} aria-label={`Remove filter: ${label}`}>
        <CloseIcon size={16} />
      </Link>
    </li>
  );
}

export interface ActiveFiltersProps {
  chips: ChipProps[];
  clearHref: string;
}

export function ActiveFilters({ chips, clearHref }: ActiveFiltersProps) {
  if (chips.length === 0) return null;
  return (
    <ul className={styles.list} aria-label="Active filters">
      {chips.map((chip) => (
        <Chip key={`${chip.label}-${chip.removeHref}`} {...chip} />
      ))}
      <li>
        <Link href={clearHref} className={styles.clear}>
          Clear all
        </Link>
      </li>
    </ul>
  );
}
