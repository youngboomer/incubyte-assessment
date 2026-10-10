import { useId, type ComponentProps, type ReactNode } from "react";
import { cx } from "./cx";
import styles from "./field.module.css";

export interface FieldChrome {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  fieldClassName?: string;
}

export interface FieldProps extends FieldChrome {
  id: string;
  children: ReactNode;
}

export function Field({ id, label, hint, error, required, fieldClassName, children }: FieldProps) {
  return (
    <div className={cx(styles.field, fieldClassName)}>
      <label htmlFor={id} className={styles.label}>
        {label}
        {required ? (
          <span className={styles.required} aria-hidden="true">
            {" "}
            *
          </span>
        ) : null}
      </label>
      {children}
      {hint ? (
        <p id={`${id}-hint`} className={styles.hint}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} className={styles.error}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

function wiring(id: string, chrome: Pick<FieldChrome, "hint" | "error" | "required">) {
  const describedBy = [chrome.hint ? `${id}-hint` : null, chrome.error ? `${id}-error` : null]
    .filter(Boolean)
    .join(" ");
  return {
    id,
    required: chrome.required,
    "aria-invalid": chrome.error ? true : undefined,
    "aria-describedby": describedBy || undefined,
  } as const;
}

export interface InputProps extends Omit<ComponentProps<"input">, "id">, FieldChrome {
  id?: string;
}

export function Input({ id, label, hint, error, required, fieldClassName, className, ...rest }: InputProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <Field id={fieldId} {...{ label, hint, error, required, fieldClassName }}>
      <input
        {...rest}
        {...wiring(fieldId, { hint, error, required })}
        className={cx(styles.control, className)}
      />
    </Field>
  );
}

export interface SelectProps extends Omit<ComponentProps<"select">, "id">, FieldChrome {
  id?: string;
}

export function Select({
  id,
  label,
  hint,
  error,
  required,
  fieldClassName,
  className,
  children,
  ...rest
}: SelectProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <Field id={fieldId} {...{ label, hint, error, required, fieldClassName }}>
      <select
        {...rest}
        {...wiring(fieldId, { hint, error, required })}
        className={cx(styles.control, styles.select, className)}
      >
        {children}
      </select>
    </Field>
  );
}

export interface TextareaProps extends Omit<ComponentProps<"textarea">, "id">, FieldChrome {
  id?: string;
}

export function Textarea({
  id,
  label,
  hint,
  error,
  required,
  fieldClassName,
  className,
  rows = 3,
  ...rest
}: TextareaProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <Field id={fieldId} {...{ label, hint, error, required, fieldClassName }}>
      <textarea
        {...rest}
        rows={rows}
        {...wiring(fieldId, { hint, error, required })}
        className={cx(styles.control, styles.textarea, className)}
      />
    </Field>
  );
}

export interface MoneyInputProps extends Omit<ComponentProps<"input">, "id" | "type" | "prefix">, FieldChrome {
  id?: string;
  currencySymbol: string;
}

export function MoneyInput({
  id,
  label,
  hint,
  error,
  required,
  fieldClassName,
  className,
  currencySymbol,
  ...rest
}: MoneyInputProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <Field id={fieldId} {...{ label, hint, error, required, fieldClassName }}>
      <span className={cx(styles.moneyWrap, Boolean(error) && styles.invalid)}>
        <span className={styles.prefix} aria-hidden="true">
          {currencySymbol}
        </span>
        <input
          {...rest}
          {...wiring(fieldId, { hint, error, required })}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          className={cx(styles.moneyInput, className)}
        />
      </span>
    </Field>
  );
}
