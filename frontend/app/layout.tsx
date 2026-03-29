import type { Metadata } from "next";
import Link from "next/link";
import { Inter } from "next/font/google";

import { Providers } from "@/components/providers";
import { FinanceBackground } from "@/components/ui/finance-background";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "DhanRakshak",
  description: "AI-powered personal finance mentor",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <FinanceBackground />
        <Link
          href="/dashboard"
          className="fixed left-4 top-4 z-50 rounded-full border border-accent/80 bg-accent px-4 py-1.5 text-xs font-extrabold uppercase tracking-[0.14em] text-black shadow-[0_8px_24px_rgba(0,255,163,0.35)] ring-2 ring-accent/35 transition hover:scale-[1.03] hover:shadow-[0_10px_30px_rgba(0,255,163,0.45)]"
          aria-label="DhanRakshak home"
        >
          DhanRakshak
        </Link>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
