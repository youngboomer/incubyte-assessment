import type { ReactNode, SVGProps } from "react";

export interface IconProps extends Omit<SVGProps<SVGSVGElement>, "children"> {
  size?: 16 | 20;
}

function Svg({ size = 20, children, ...rest }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export function PeopleIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="7" cy="6" r="3" />
      <path d="M1.5 17c0-3 2.5-5 5.5-5s5.5 2 5.5 5M13 3.2a3 3 0 0 1 0 5.6M14 12.2c2.4.4 4 2.1 4 4.8" />
    </Svg>
  );
}

export function PaymentsIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="2" y="5" width="16" height="10" rx="1.5" />
      <circle cx="10" cy="10" r="2.2" />
      <path d="M5 8v.01M15 12v.01" />
    </Svg>
  );
}

export function TuneIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 5h7M16 5h1M3 10h2M11 10h6M3 15h8M17 15h0" />
      <circle cx="13" cy="5" r="1.6" />
      <circle cx="8" cy="10" r="1.6" />
      <circle cx="14" cy="15" r="1.6" />
    </Svg>
  );
}

export function HistoryIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 10a7 7 0 1 0 2.2-5.1M3 3.5v3h3M10 6v4l2.5 1.5" />
    </Svg>
  );
}

export function LogoutIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 3H4.5A1.5 1.5 0 0 0 3 4.5v11A1.5 1.5 0 0 0 4.5 17H8M12.5 6.5 16 10l-3.5 3.5M16 10H8" />
    </Svg>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="9" cy="9" r="5.5" />
      <path d="m13.2 13.2 4 4" />
    </Svg>
  );
}

export function DownloadIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10 3v10M6 9.5l4 4 4-4M4 16.5h12" />
    </Svg>
  );
}

export function AddIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10 4v12M4 10h12" />
    </Svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m5 5 10 10M15 5 5 15" />
    </Svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m5 8 5 5 5-5" />
    </Svg>
  );
}

export function ChevronLeftIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m12 5-5 5 5 5" />
    </Svg>
  );
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m8 5 5 5-5 5" />
    </Svg>
  );
}

export function ArrowUpIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10 16V4M5 9l5-5 5 5" />
    </Svg>
  );
}

export function ArrowDownIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10 4v12M5 11l5 5 5-5" />
    </Svg>
  );
}

export function WarningIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10 3.5 18 17H2L10 3.5ZM10 8.5v4M10 14.8v.01" />
    </Svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m4 10.5 4 4 8-9" />
    </Svg>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 5.5h14M3 10h14M3 14.5h14" />
    </Svg>
  );
}

export function RefreshIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M16.5 10a6.5 6.5 0 1 1-2-4.7M16.5 3.5v3.5H13" />
    </Svg>
  );
}

export function InfoIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 9v5M10 6.2v.01" />
    </Svg>
  );
}
