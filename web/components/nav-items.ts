export type NavIcon = "people" | "payments" | "tune" | "history";

export interface NavItem {
  href: string;
  label: string;
  icon: NavIcon;
  exact?: boolean;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/employees", label: "Employees", icon: "people" },
  { href: "/", label: "Pay overview", icon: "payments", exact: true },
  { href: "/planning-rates", label: "Planning rates", icon: "tune" },
  { href: "/history", label: "Change history", icon: "history" },
];
