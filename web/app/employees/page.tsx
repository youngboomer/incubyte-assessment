import Link from "next/link";
import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { Shell } from "../../components/shell";
import { AddIcon, DownloadIcon, RefreshIcon } from "../../components/icons";
import {
  ActiveFilters,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  LinkButton,
  Money,
  PageHeader,
  Pagination,
  Select,
  SortHeader,
  StatusTag,
  Td,
  Th,
} from "../../components/ui";
import type { ChipProps } from "../../components/ui";
import { listEmployees, reference } from "../../lib/endpoints";
import { formatLocalMoney, formatUsd, fullName } from "../../lib/format";
import { directoryQuery } from "../../lib/query";
import type { SearchParams } from "../../lib/query";
import { SESSION_COOKIE } from "../../lib/session";
import type { DirectoryFilters, Employee, Reference } from "../../lib/types";
import {
  DEFAULT_LIMIT,
  PAGE_SIZES,
  activeFilterCount,
  backendFilters,
  clearedFilters,
  currentPage,
  directoryHref,
  nextSort,
  pageRange,
  readDirectoryState,
  without,
  withoutPaging,
} from "./directory-url";
import type { DirectoryState } from "./directory-url";
import styles from "./employees.module.css";

export const metadata = { title: "Employees | CompPulse" };

const BASE = "/employees";

const SORT_OPTIONS = [
  { value: "name", label: "Name" },
  { value: "title", label: "Title" },
  { value: "department", label: "Department" },
  { value: "country", label: "Country" },
  { value: "salary_usd", label: "Pay (USD)" },
  { value: "base_salary", label: "Base pay (local)" },
  { value: "hire_date", label: "Hire date" },
  { value: "employee_number", label: "Employee number" },
] as const;

const usdFormat = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
  minimumFractionDigits: 0,
});

function dollars(value: string): string {
  return usdFormat.format(Number(value));
}

function title(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function payChip(state: DirectoryState): string | null {
  const { pay_min: min, pay_max: max } = state;
  if (min !== undefined && max !== undefined) {
    return `Pay: ${dollars(min)} to ${dollars(max)}`;
  }
  if (min !== undefined) {
    return `Pay: from ${dollars(min)}`;
  }
  if (max !== undefined) {
    return `Pay: up to ${dollars(max)}`;
  }
  return null;
}

function chipsFor(state: DirectoryState, ref: Reference | null): ChipProps[] {
  const chips: ChipProps[] = [];
  const add = (label: string, ...keys: (keyof DirectoryState)[]) =>
    chips.push({ label, removeHref: directoryHref(BASE, without(state, ...keys)) });
  if (state.q !== undefined) {
    add(`Search: ${state.q}`, "q");
  }
  if (state.country !== undefined) {
    const name = ref?.countries.find((item) => item.code === state.country)?.name;
    add(`Country: ${name ?? state.country}`, "country");
  }
  if (state.department_id !== undefined) {
    const name = ref?.departments.find((item) => String(item.id) === state.department_id)?.name;
    add(`Department: ${name ?? state.department_id}`, "department_id");
  }
  if (state.level !== undefined) {
    add(`Level: ${state.level}`, "level");
  }
  if (state.status !== undefined) {
    add(`Status: ${title(state.status)}`, "status");
  }
  const pay = payChip(state);
  if (pay !== null) {
    add(pay, "pay_min", "pay_max");
  }
  return chips;
}

function payOf(employee: Employee) {
  const total = (BigInt(employee.base_salary_scaled) + BigInt(employee.variable_pay_scaled)).toString();
  return {
    local: formatLocalMoney(total, employee.salary_scale, employee.currency_code),
    usd:
      employee.currency_code === "USD"
        ? undefined
        : `${formatUsd(employee.salary_usd_scaled, employee.salary_usd_scale)} USD`,
  };
}

type PageProps = { searchParams: Promise<SearchParams> };

export default async function EmployeesPage({ searchParams }: PageProps) {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }

  const state = readDirectoryState(await searchParams);
  const filters = backendFilters(state);
  const [directory, ref] = await Promise.all([
    listEmployees(token, filters),
    reference(token),
  ]);

  const failure = !directory.ok ? directory : !ref.ok ? ref : null;
  if (failure?.code === "unauthorized") {
    redirect("/logout");
  }
  if (failure && state.cursor !== undefined && failure.status === 422) {
    redirect(directoryHref(BASE, withoutPaging(state)));
  }
  if (!directory.ok || !ref.ok) {
    return (
      <Shell>
        <PageHeader title="Employees" />
        <EmptyState
          title="Could not load employees."
          action={
            <LinkButton href={directoryHref(BASE, state)} variant="quiet" icon={<RefreshIcon size={16} />}>
              Retry
            </LinkButton>
          }
        >
          Check your connection and try again.
        </EmptyState>
      </Shell>
    );
  }

  const page = directory.data;
  const reference_ = ref.data;
  const limit = filters.limit ?? DEFAULT_LIMIT;
  const pageNumber = currentPage(state);
  const range = pageRange(pageNumber, limit, page.items.length, page.total);
  const chips = chipsFor(state, reference_);
  const clearHref = directoryHref(BASE, clearedFilters(state));
  const exportFilters: DirectoryFilters = { ...filters };
  delete exportFilters.cursor;
  delete exportFilters.limit;

  const pageHref = (cursor: string | null, target: number): string | null => {
    if (cursor === null) {
      return null;
    }
    const rest = withoutPaging(state);
    return directoryHref(BASE, target <= 1 ? rest : { ...rest, cursor, page: String(target) });
  };

  const sorted = (key: string) => nextSort(state, key);
  const header = (key: string, label: string, numeric = false) => {
    const { href, direction } = sorted(key);
    return (
      <SortHeader href={directoryHref(BASE, href)} direction={direction === null ? null : direction} numeric={numeric}>
        {label}
      </SortHeader>
    );
  };

  const hiddenForSize = Object.fromEntries(
    Object.entries(withoutPaging(state)).filter(([key]) => key !== "limit"),
  ) as Record<string, string>;
  const hiddenForFilters: Record<string, string> = {};
  if (state.limit !== undefined) {
    hiddenForFilters["limit"] = state.limit;
  }

  return (
    <Shell>
      <PageHeader
        title="Employees"
        count={`${page.total.toLocaleString("en-US")} ${page.total === 1 ? "person" : "people"}`}
        actions={
          <>
            <LinkButton
              href={`/employees/export${directoryQuery(exportFilters)}`}
              variant="quiet"
              icon={<DownloadIcon size={16} />}
              prefetch={false}
            >
              Export CSV
            </LinkButton>
            <LinkButton href="/employees/new" icon={<AddIcon size={16} />}>
              Add employee
            </LinkButton>
          </>
        }
      />

      <FilterBar
        search={{
          name: "q",
          defaultValue: state.q,
          label: "Search employees",
          placeholder: "Search by name, email or employee number",
        }}
        activeCount={activeFilterCount(state) - (state.q === undefined ? 0 : 1)}
        hidden={hiddenForFilters}
        submitLabel="Apply filters"
        chips={<ActiveFilters chips={chips} clearHref={clearHref} />}
      >
        <Select name="country" label="Country" defaultValue={state.country ?? ""}>
          <option value="">All countries</option>
          {reference_.countries.map((country) => (
            <option key={country.code} value={country.code}>
              {country.name}
            </option>
          ))}
        </Select>
        <Select name="department_id" label="Department" defaultValue={state.department_id ?? ""}>
          <option value="">All departments</option>
          {reference_.departments.map((department) => (
            <option key={department.id} value={String(department.id)}>
              {department.name}
            </option>
          ))}
        </Select>
        <Select name="level" label="Level" defaultValue={state.level ?? ""}>
          <option value="">All levels</option>
          {reference_.levels.map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </Select>
        <Select name="status" label="Status" defaultValue={state.status ?? ""}>
          <option value="">All statuses</option>
          {reference_.statuses.map((status) => (
            <option key={status} value={status}>
              {title(status)}
            </option>
          ))}
        </Select>
        <Select name="sort" label="Sort by" defaultValue={state.sort ?? "name"}>
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
        <Select name="direction" label="Order" defaultValue={state.direction ?? "asc"}>
          <option value="asc">Ascending</option>
          <option value="desc">Descending</option>
        </Select>
        <Input
          name="pay_min"
          label="Min pay (USD)"
          type="number"
          min={0}
          step="any"
          inputMode="decimal"
          placeholder="0"
          defaultValue={state.pay_min}
        />
        <Input
          name="pay_max"
          label="Max pay (USD)"
          type="number"
          min={0}
          step="any"
          inputMode="decimal"
          placeholder="No limit"
          defaultValue={state.pay_max}
        />
      </FilterBar>

      {page.items.length === 0 ? (
        <EmptyState
          title="No employees match these filters."
          action={
            <LinkButton href={clearHref} variant="quiet">
              Clear filters
            </LinkButton>
          }
        >
          Try a different search or remove a filter.
        </EmptyState>
      ) : (
        <>
          <DataTable caption="Employees">
            <thead>
              <tr>
                {header("name", "Name")}
                {header("title", "Title")}
                {header("department", "Department")}
                {header("country", "Country")}
                <Th>Level</Th>
                {header("salary_usd", "Pay (local / USD)", true)}
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((employee) => {
                const pay = payOf(employee);
                return (
                  <tr key={employee.id}>
                    <Td label="Name" primary>
                      <span className={styles.person}>
                        <Link href={`/employees/${employee.id}`} className={styles.name}>
                          {fullName(employee)}
                        </Link>
                        <span className={styles.number}>{employee.employee_number}</span>
                      </span>
                    </Td>
                    <Td label="Title">{employee.job_title}</Td>
                    <Td label="Department">{employee.department.name}</Td>
                    <Td label="Country">{employee.country.name}</Td>
                    <Td label="Level">{employee.level}</Td>
                    <Td label="Pay" numeric>
                      <Money local={pay.local} usd={pay.usd} />
                    </Td>
                    <Td label="Status">
                      <StatusTag status={employee.status === "terminated" ? "Terminated" : "Active"} />
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
          <Pagination
            from={range.from}
            to={range.to}
            total={page.total}
            previousHref={pageHref(page.prev_cursor, pageNumber - 1)}
            nextHref={pageHref(page.next_cursor, pageNumber + 1)}
            pageSize={{ name: "limit", value: limit, options: PAGE_SIZES, hidden: hiddenForSize }}
          />
        </>
      )}
    </Shell>
  );
}
