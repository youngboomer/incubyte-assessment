import { cookies } from "next/headers";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import { Shell } from "../../components/shell";
import { backendFetch } from "../../lib/api";
import { formatScaled } from "../../lib/format";
import { SESSION_COOKIE } from "../../lib/session";
import type { DirectoryPage, Employee, Reference } from "../../lib/types";
import { AddForm } from "./add-form";
import styles from "./employees.module.css";

const SORTS = [
  "name",
  "employee_number",
  "department",
  "country",
  "title",
  "base_salary",
  "salary_usd",
  "hire_date",
] as const;

type SortKey = (typeof SORTS)[number];
type Direction = "asc" | "desc";

type DirectoryQuery = {
  q: string;
  departmentId: string;
  country: string;
  currency: string;
  status: string;
  sort: SortKey;
  direction: Direction;
  cursor: string;
  limit: number;
};

type Choice = {
  value: string;
  label: string;
};

type LoadResult = {
  directory: DirectoryPage | null;
  reference: Reference | null;
  status: number | null;
};

type EmployeesPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function EmployeesPage({ searchParams }: EmployeesPageProps) {
  await connection();
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    redirect("/login");
  }

  const query = readQuery(await searchParams);
  const loaded = await loadDirectory(token, query);
  const currentQuery = exportQuery(query);

  return (
    <Shell>
      <h1>Employees</h1>
      <FilterForm query={query} reference={loaded.reference} />
      <p className={styles.download}>
        <a href={"/employees/export" + currentQuery}>Download CSV</a>
      </p>
      {loaded.directory ? (
        <DirectoryResults query={query} page={loaded.directory} />
      ) : (
        <p className={styles.error}>{loadError(loaded.status)}</p>
      )}
      {loaded.reference ? (
        <AddForm
          departments={loaded.reference.departments}
          countries={loaded.reference.countries}
          currencies={loaded.reference.currencies}
          levels={loaded.reference.levels}
          statuses={loaded.reference.statuses}
        />
      ) : null}
    </Shell>
  );
}

function DirectoryResults({ query, page }: { query: DirectoryQuery; page: DirectoryPage }) {
  return (
    <>
      <p className={styles.total}>Total {page.total}</p>
      {page.items.length === 0 ? (
        <p className={styles.empty}>No employees match these filters.</p>
      ) : (
        <div className={styles.wrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <SortHeader query={query} column="name" label="Name" />
                <SortHeader query={query} column="employee_number" label="Employee number" />
                <th scope="col">Email</th>
                <SortHeader query={query} column="title" label="Title" />
                <SortHeader query={query} column="department" label="Department" />
                <SortHeader query={query} column="country" label="Country" />
                <th scope="col">Currency</th>
                <th scope="col">Level</th>
                <SortHeader query={query} column="base_salary" label="Base salary" />
                <SortHeader query={query} column="salary_usd" label="USD salary" />
                <th scope="col">Status</th>
                <SortHeader query={query} column="hire_date" label="Hire date" />
              </tr>
            </thead>
            <tbody>
              {page.items.map((employee) => (
                <EmployeeRow key={employee.id} employee={employee} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pager query={query} page={page} />
    </>
  );
}

function EmployeeRow({ employee }: { employee: Employee }) {
  return (
    <tr>
      <td>
        <a href={`/employees/${employee.id}`}>
          {employee.first_name} {employee.last_name}
        </a>
      </td>
      <td>{employee.employee_number}</td>
      <td>{employee.email}</td>
      <td>{employee.job_title}</td>
      <td>{employee.department.name}</td>
      <td>{employee.country.name}</td>
      <td>{employee.currency_code}</td>
      <td>{employee.level}</td>
      <td className={styles.numeric}>
        {formatScaled(employee.base_salary_scaled, employee.salary_scale, employee.currency_code)}
      </td>
      <td className={styles.numeric}>
        {formatScaled(employee.salary_usd_scaled, employee.salary_usd_scale, "USD")}
      </td>
      <td>{employee.status}</td>
      <td>{employee.hire_date}</td>
    </tr>
  );
}

function SortHeader({
  query,
  column,
  label,
}: {
  query: DirectoryQuery;
  column: SortKey;
  label: string;
}) {
  const active = query.sort === column;
  return (
    <th
      scope="col"
      aria-sort={active ? (query.direction === "asc" ? "ascending" : "descending") : "none"}
    >
      <a href={sortHref(query, column)} className={active ? styles.active : undefined}>
        {label}
        {active ? ` (${query.direction})` : ""}
      </a>
    </th>
  );
}

function Pager({ query, page }: { query: DirectoryQuery; page: DirectoryPage }) {
  if (!page.prev_cursor && !page.next_cursor) {
    return null;
  }
  return (
    <nav className={styles.pager} aria-label="Pagination">
      {page.prev_cursor ? <a href={pageHref(query, page.prev_cursor)}>Previous</a> : null}
      {page.next_cursor ? <a href={pageHref(query, page.next_cursor)}>Next</a> : null}
    </nav>
  );
}

function FilterForm({
  query,
  reference,
}: {
  query: DirectoryQuery;
  reference: Reference | null;
}) {
  const departments = reference
    ? reference.departments.map((department) => ({
        value: String(department.id),
        label: department.name,
      }))
    : null;
  const countries = reference
    ? reference.countries.map((country) => ({
        value: country.code,
        label: country.name,
      }))
    : null;
  const currencies = reference
    ? reference.currencies.map((currency) => ({
        value: currency.code,
        label: currency.code,
      }))
    : null;
  const statuses = reference
    ? reference.statuses.map((status) => ({ value: status, label: status }))
    : null;

  return (
    <form method="get" action="/employees" className={styles.filters}>
      <label className={styles.search}>
        Search
        <input name="q" type="search" defaultValue={query.q} />
      </label>
      <ChoiceFilter
        label="Department"
        name="department_id"
        value={query.departmentId}
        options={departments}
        allLabel="All departments"
      />
      <ChoiceFilter
        label="Country"
        name="country"
        value={query.country}
        options={countries}
        allLabel="All countries"
      />
      <ChoiceFilter
        label="Currency"
        name="currency"
        value={query.currency}
        options={currencies}
        allLabel="All currencies"
      />
      <ChoiceFilter
        label="Status"
        name="status"
        value={query.status}
        options={statuses}
        allLabel="All statuses"
      />
      <label className={styles.limit}>
        Limit
        <input name="limit" type="number" min={1} max={100} defaultValue={query.limit} required />
      </label>
      <label className={styles.srOnly}>
        Sort
        <input type="hidden" name="sort" value={query.sort} />
      </label>
      <label className={styles.srOnly}>
        Direction
        <input type="hidden" name="direction" value={query.direction} />
      </label>
      <button type="submit">Apply</button>
    </form>
  );
}

function ChoiceFilter({
  label,
  name,
  value,
  options,
  allLabel,
}: {
  label: string;
  name: string;
  value: string;
  options: readonly Choice[] | null;
  allLabel: string;
}) {
  if (!options) {
    return (
      <label>
        {label}
        <input name={name} defaultValue={value} />
      </label>
    );
  }
  const choices = withCurrent(options, value);
  return (
    <label>
      {label}
      <select name={name} defaultValue={value}>
        <option value="">{allLabel}</option>
        {choices.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

async function loadDirectory(token: string, query: DirectoryQuery): Promise<LoadResult> {
  const [employeesResponse, referenceResponse] = await Promise.all([
    fetchBackend(employeesPath(query), token),
    fetchBackend("/reference", token),
  ]);

  if (employeesResponse?.status === 401 || referenceResponse?.status === 401) {
    redirect("/logout");
  }

  const reference = referenceResponse?.ok ? await readReference(referenceResponse) : null;
  if (!employeesResponse) {
    return { directory: null, reference, status: null };
  }
  if (!employeesResponse.ok) {
    return { directory: null, reference, status: employeesResponse.status };
  }
  const directory = await readDirectory(employeesResponse);
  if (!directory) {
    return { directory: null, reference, status: employeesResponse.status };
  }
  return { directory, reference, status: null };
}

async function fetchBackend(path: string, token: string): Promise<Response | null> {
  try {
    return await backendFetch(path, token);
  } catch {
    return null;
  }
}

async function readDirectory(response: Response): Promise<DirectoryPage | null> {
  try {
    const body: unknown = await response.json();
    if (!isDirectoryPage(body)) {
      return null;
    }
    return body;
  } catch {
    return null;
  }
}

async function readReference(response: Response): Promise<Reference | null> {
  try {
    const body: unknown = await response.json();
    if (!isReference(body)) {
      return null;
    }
    return body;
  } catch {
    return null;
  }
}

function isDirectoryPage(value: unknown): value is DirectoryPage {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const page = value as Partial<DirectoryPage>;
  return (
    Array.isArray(page.items) &&
    page.items.every(isEmployee) &&
    (page.next_cursor === null || typeof page.next_cursor === "string") &&
    (page.prev_cursor === null || typeof page.prev_cursor === "string") &&
    typeof page.total === "number"
  );
}

function isEmployee(value: unknown): value is Employee {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const employee = value as Partial<Employee>;
  const department = employee.department;
  const country = employee.country;
  return (
    typeof employee.id === "string" &&
    typeof employee.first_name === "string" &&
    typeof employee.last_name === "string" &&
    typeof employee.employee_number === "string" &&
    typeof employee.email === "string" &&
    typeof employee.job_title === "string" &&
    typeof department === "object" &&
    department !== null &&
    typeof department.name === "string" &&
    typeof country === "object" &&
    country !== null &&
    typeof country.name === "string" &&
    typeof employee.currency_code === "string" &&
    typeof employee.level === "string" &&
    typeof employee.base_salary_scaled === "string" &&
    typeof employee.salary_scale === "number" &&
    typeof employee.salary_usd_scaled === "string" &&
    typeof employee.salary_usd_scale === "number" &&
    typeof employee.status === "string" &&
    typeof employee.hire_date === "string"
  );
}

function isReference(value: unknown): value is Reference {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const reference = value as Partial<Reference>;
  return (
    Array.isArray(reference.departments) &&
    reference.departments.every(isDepartment) &&
    Array.isArray(reference.countries) &&
    reference.countries.every(isCountry) &&
    Array.isArray(reference.currencies) &&
    reference.currencies.every(isCurrency) &&
    isStringList(reference.levels) &&
    isStringList(reference.statuses)
  );
}

function isDepartment(value: unknown): boolean {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const department = value as { id?: unknown; name?: unknown };
  return typeof department.id === "number" && typeof department.name === "string";
}

function isCountry(value: unknown): boolean {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const country = value as { code?: unknown; name?: unknown; currency_code?: unknown };
  return (
    typeof country.code === "string" &&
    typeof country.name === "string" &&
    typeof country.currency_code === "string"
  );
}

function isCurrency(value: unknown): boolean {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const currency = value as {
    code?: unknown;
    name?: unknown;
    minor_scale?: unknown;
    units_per_usd_scaled?: unknown;
    units_per_usd_scale?: unknown;
  };
  return (
    typeof currency.code === "string" &&
    typeof currency.name === "string" &&
    typeof currency.minor_scale === "number" &&
    typeof currency.units_per_usd_scaled === "string" &&
    typeof currency.units_per_usd_scale === "number"
  );
}

function isStringList(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function loadError(status: number | null): string {
  if (status === null) {
    return "Could not load employees.";
  }
  return `Could not load employees. ${status}`;
}

function readQuery(params: Record<string, string | string[] | undefined>): DirectoryQuery {
  const sortRaw = firstParam(params.sort).trim();
  const directionRaw = firstParam(params.direction).trim();
  const limitRaw = firstParam(params.limit).trim();
  const limitNumber = Number(limitRaw);
  const sortValid = sortRaw === "" || isSort(sortRaw);
  const directionValid = directionRaw === "" || directionRaw === "asc" || directionRaw === "desc";
  const cursorRaw = firstParam(params.cursor);
  return {
    q: firstParam(params.q).trim(),
    departmentId: firstParam(params.department_id).trim(),
    country: firstParam(params.country).trim(),
    currency: firstParam(params.currency).trim(),
    status: firstParam(params.status).trim(),
    sort: isSort(sortRaw) ? sortRaw : "name",
    direction: directionRaw === "desc" ? "desc" : "asc",
    cursor: sortValid && directionValid && cursorRaw.trim() !== "" ? cursorRaw : "",
    limit:
      limitRaw !== "" && Number.isInteger(limitNumber) && limitNumber >= 1 && limitNumber <= 100
        ? limitNumber
        : 50,
  };
}

function employeesPath(query: DirectoryQuery): string {
  const params = filterParams(query);
  params.set("sort", query.sort);
  params.set("direction", query.direction);
  params.set("limit", String(query.limit));
  if (query.cursor) {
    params.set("cursor", query.cursor);
  }
  return `/employees?${params.toString()}`;
}

function exportQuery(query: DirectoryQuery): string {
  const params = filterParams(query);
  params.set("sort", query.sort);
  params.set("direction", query.direction);
  return `?${params.toString()}`;
}

function sortHref(query: DirectoryQuery, column: SortKey): string {
  const direction: Direction = query.sort === column && query.direction === "asc" ? "desc" : "asc";
  return hrefFor({ ...query, sort: column, direction, cursor: "" });
}

function pageHref(query: DirectoryQuery, cursor: string): string {
  return hrefFor({ ...query, cursor });
}

function hrefFor(query: DirectoryQuery): string {
  const params = filterParams(query);
  if (query.sort !== "name") {
    params.set("sort", query.sort);
  }
  if (query.direction !== "asc") {
    params.set("direction", query.direction);
  }
  if (query.limit !== 50) {
    params.set("limit", String(query.limit));
  }
  if (query.cursor) {
    params.set("cursor", query.cursor);
  }
  const queryString = params.toString();
  return queryString ? `/employees?${queryString}` : "/employees";
}

function filterParams(query: DirectoryQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) {
    params.set("q", query.q);
  }
  if (query.departmentId) {
    params.set("department_id", query.departmentId);
  }
  if (query.country) {
    params.set("country", query.country);
  }
  if (query.currency) {
    params.set("currency", query.currency);
  }
  if (query.status) {
    params.set("status", query.status);
  }
  return params;
}

function withCurrent(options: readonly Choice[], current: string): Choice[] {
  if (current === "" || options.some((option) => option.value === current)) {
    return [...options];
  }
  return [...options, { value: current, label: current }];
}

function firstParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function isSort(value: string): value is SortKey {
  return (SORTS as readonly string[]).includes(value);
}
