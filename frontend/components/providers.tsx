"use client";

import { useEffect } from "react";
import { Toaster } from "react-hot-toast";

import { useAuth } from "@/hooks/useAuth";

export function Providers({ children }: { children: React.ReactNode }) {
  const loadToken = useAuth((state) => state.loadToken);

  useEffect(() => {
    loadToken();
  }, [loadToken]);

  return (
    <>
      {children}
      <Toaster position="top-right" toastOptions={{ style: { background: "#101826", color: "#e7edf9" } }} />
    </>
  );
}
