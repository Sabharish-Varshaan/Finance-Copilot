import axios from "axios";

import api from "@/services/api";
import type { Goal } from "@/types";

export type GoalStatusFilter = "active" | "paused" | "completed" | "all";

export interface GoalCreatePayload {
  category: string;
  title: string;
  target_amount: number;
  current_amount: number;
  target_date: string;
  expected_annual_return: number;
  smart_adjust?: boolean;
}

export interface GoalUpdatePayload {
  title?: string;
  target_amount?: number;
  current_amount?: number;
  target_date?: string;
  expected_annual_return?: number;
  monthly_sip_required?: number;
  status?: "active" | "paused" | "completed";
}

export interface GoalAutoAdjustment {
  adjusted_years: number;
  adjusted_target_date: string;
  feasible_sip: number;
}

export interface GoalFeasibilityError {
  valid: false;
  reason: string;
  required_sip: number;
  available_savings: number;
  suggested_sip: number;
  suggestions: string[];
  auto_adjustment?: GoalAutoAdjustment;
}

export async function listGoals(status: GoalStatusFilter = "active") {
  const response = await api.get<Goal[]>("/goals", { params: { status } });
  return response.data;
}

export async function createGoal(payload: GoalCreatePayload) {
  const response = await api.post<Goal>("/goals", payload);
  return response.data;
}

export async function updateGoal(goalId: number, payload: GoalUpdatePayload) {
  const response = await api.patch<Goal>(`/goals/${goalId}`, payload);
  return response.data;
}

export async function deleteGoal(goalId: number) {
  await api.delete(`/goals/${goalId}`);
}

export function extractGoalFeasibilityError(error: unknown): GoalFeasibilityError | null {
  if (!axios.isAxiosError(error)) {
    return null;
  }

  const detail = error.response?.data?.detail;
  if (!detail || typeof detail !== "object") {
    return null;
  }

  const candidate = detail as Partial<GoalFeasibilityError>;
  if (candidate.valid !== false || typeof candidate.reason !== "string") {
    return null;
  }

  if (
    typeof candidate.required_sip !== "number" ||
    typeof candidate.available_savings !== "number" ||
    typeof candidate.suggested_sip !== "number" ||
    !Array.isArray(candidate.suggestions)
  ) {
    return null;
  }

  return {
    valid: false,
    reason: candidate.reason,
    required_sip: candidate.required_sip,
    available_savings: candidate.available_savings,
    suggested_sip: candidate.suggested_sip,
    suggestions: candidate.suggestions.map((item) => String(item)),
    auto_adjustment: candidate.auto_adjustment,
  };
}
