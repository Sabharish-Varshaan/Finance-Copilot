import { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div
      className={cn(
        "panel-glass neon-outline rounded-2xl border border-borderSoft/70 bg-panel/85 p-5 shadow-card transition-all duration-300 ease-smooth hover:-translate-y-0.5 hover:shadow-glow",
        className,
      )}
    >
      {children}
    </div>
  );
}
