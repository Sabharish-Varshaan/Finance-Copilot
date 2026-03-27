import { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
}

export function Button({ className, isLoading, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "pulse-soft relative inline-flex items-center justify-center overflow-hidden rounded-full border border-accent/30 bg-accent px-5 py-2.5 text-sm font-semibold text-[#05110d] shadow-[0_0_18px_rgba(0,255,163,0.28)] transition-all duration-300 ease-smooth before:absolute before:inset-0 before:bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.35),transparent_55%)] hover:-translate-y-0.5 hover:shadow-[0_0_28px_rgba(0,255,163,0.38)] disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      disabled={isLoading || props.disabled}
      {...props}
    >
      <span className="relative z-10">{isLoading ? "Please wait..." : children}</span>
    </button>
  );
}
