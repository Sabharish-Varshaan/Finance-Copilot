import api from "@/services/api";
import type { User } from "@/types";

export async function registerUser(email: string, password: string) {
  const response = await api.post<User>("/auth/register", { email, password });
  return response.data;
}

export async function loginUser(email: string, password: string) {
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);

  const response = await api.post<{ access_token: string; token_type: string }>("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  return response.data;
}
