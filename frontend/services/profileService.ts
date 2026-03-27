import api from "@/services/api";
import type { FinancialProfilePayload } from "@/types";

export async function upsertProfile(payload: FinancialProfilePayload) {
  const response = await api.put("/finance/profile", payload);
  return response.data;
}

export async function getProfile() {
  const response = await api.get("/finance/profile");
  return response.data;
}
