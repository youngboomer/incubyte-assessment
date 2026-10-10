import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import { cx } from "./cx";
import styles from "./button.module.css";

export type ButtonVariant = "primary" | "quiet" | "danger";
export type ButtonSize = "sm" | "md";

interface CommonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
}

function classes({ variant = "primary", size = "md" }: CommonProps, extra?: string) {
  return cx(styles.button, styles[variant], styles[size], extra);
}

export interface ButtonProps extends Omit<ComponentProps<"button">, "children">, CommonProps {
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant,
  size,
  icon,
  loading = false,
  disabled,
  className,
  type = "button",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={classes({ variant, size }, className)}
    >
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : icon}
      {children}
    </button>
  );
}

export interface LinkButtonProps extends Omit<ComponentProps<typeof Link>, "children">, CommonProps {
  disabled?: boolean;
  children: ReactNode;
}

export function LinkButton({
  variant,
  size,
  icon,
  disabled = false,
  className,
  children,
  ...rest
}: LinkButtonProps) {
  return (
    <Link
      {...rest}
      className={classes({ variant, size }, className)}
      aria-disabled={disabled || undefined}
      tabIndex={disabled ? -1 : rest.tabIndex}
    >
      {icon}
      {children}
    </Link>
  );
}
