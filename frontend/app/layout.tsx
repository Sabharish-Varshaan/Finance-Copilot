import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Providers } from "@/components/providers";
import { FinanceBackground } from "@/components/ui/finance-background";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Finance Copilot",
  description: "AI-powered personal finance mentor",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <FinanceBackground />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
