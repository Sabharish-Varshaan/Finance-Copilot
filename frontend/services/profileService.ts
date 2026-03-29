import api from "@/services/api";
import type { FinancialProfilePayload, UserInvestmentCreate, UserInvestmentRead } from "@/types";

export async function upsertProfile(payload: FinancialProfilePayload) {
  const response = await api.put("/finance/profile", payload);
  return response.data;
}

export async function getProfile() {
  const response = await api.get("/finance/profile");
  return response.data;
}

export async function updateInvestment(payload: UserInvestmentCreate): Promise<UserInvestmentRead> {
  const response = await api.post("/finance/investments", payload);
  return response.data;
}
