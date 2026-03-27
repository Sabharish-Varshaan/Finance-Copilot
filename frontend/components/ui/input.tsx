import { forwardRef, InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full rounded-2xl border border-borderSoft bg-panelAlt/80 px-4 py-3 text-sm text-text placeholder:text-muted/70 outline-none transition-all duration-300 ease-smooth focus:border-accent/60 focus:shadow-[0_0_0_4px_rgba(0,255,163,0.14)]",
          className,
        )}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";
