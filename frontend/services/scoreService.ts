import api from "@/services/api";
import type { MoneyHealthScore } from "@/types";

export async function getScore() {
  const response = await api.get<MoneyHealthScore>("/finance/health-score");
  return response.data;
}

export async function getNudges() {
  const response = await api.get<{ nudges: string[] }>("/nudges");
  return response.data;
}
