import type { ReactNode } from "react";
import type { Metadata } from "next";
import { Public_Sans } from "next/font/google";
import "./globals.css";

const publicSans = Public_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-public-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CompPulse",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" className={publicSans.variable}>
      <body>{children}</body>
    </html>
  );
}
