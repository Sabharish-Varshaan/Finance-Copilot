"use client";

import Cookies from "js-cookie";
import { create } from "zustand";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  loadToken: () => void;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,
  setToken: (token: string) => {
    localStorage.setItem("fc_token", token);
    Cookies.set("fc_token", token, { expires: 7 });
    set({ token, isAuthenticated: true });
  },
  loadToken: () => {
    const token = localStorage.getItem("fc_token");
    set({ token, isAuthenticated: !!token });
  },
  logout: () => {
    localStorage.removeItem("fc_token");
    Cookies.remove("fc_token");
    set({ token: null, isAuthenticated: false });
  },
}));
