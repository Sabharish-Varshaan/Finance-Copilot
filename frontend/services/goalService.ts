import api from "@/services/api";
import type { Goal } from "@/types";

export async function listGoals() {
  const response = await api.get<Goal[]>("/goals");
  return response.data;
}

export async function createGoal(payload: {
  category: string;
  title: string;
  target_amount: number;
  current_amount: number;
  target_date: string;
  expected_annual_return: number;
}) {
  const response = await api.post<Goal>("/goals", payload);
  return response.data;
}
