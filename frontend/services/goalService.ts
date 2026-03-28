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

export interface GoalPlanningSummary {
  goal_name: string;
  raw_sip: number;
  calculated_sip: number;
  ai_sip: number;
  final_sip: number;
  sip: number;
  timeline: number;
  original_timeline: number;
  adjusted_timeline: number;
  timeline_extended: boolean;
  timeline_adjusted: boolean;
  adjusted: boolean;
  reason: string;
  ai_reasoning: string;
  backend_limit: number;
  existing_goals_sip_total: number;
  adjustment_reason_codes: string[];
  original_target_date: string;
  adjusted_target_date: string;
  new_target_date: string;
  net_savings: number;
  max_allowed_new_sip: number;
  expected_return: number;
  monthly_return: number;
  return_assumption_note: string;
  adjustment_options: string[];
}

export interface GoalCreateResponse {
  goal: Goal;
  planning: GoalPlanningSummary;
}

export interface GoalFeasibilityError {
  valid: false;
  reason: string;
  required_sip: number;
  available_savings: number;
  available_surplus?: number;
  safety_buffer_amount?: number;
  investable_surplus?: number;
  total_existing_sip?: number;
  shortfall_amount?: number;
  sip_to_investable_surplus_ratio?: number | null;
  reason_codes?: string[];
  suggested_sip: number;
  suggestions: string[];
  auto_adjustment?: GoalAutoAdjustment;
}

export async function listGoals(status: GoalStatusFilter = "active") {
  const response = await api.get<Goal[]>("/goals", { params: { status } });
  return response.data;
}

export async function createGoal(payload: GoalCreatePayload) {
  const response = await api.post<GoalCreateResponse>("/goals", payload);
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
    available_surplus: typeof candidate.available_surplus === "number" ? candidate.available_surplus : undefined,
    safety_buffer_amount: typeof candidate.safety_buffer_amount === "number" ? candidate.safety_buffer_amount : undefined,
    investable_surplus: typeof candidate.investable_surplus === "number" ? candidate.investable_surplus : undefined,
    total_existing_sip: typeof candidate.total_existing_sip === "number" ? candidate.total_existing_sip : undefined,
    shortfall_amount: typeof candidate.shortfall_amount === "number" ? candidate.shortfall_amount : undefined,
    sip_to_investable_surplus_ratio:
      typeof candidate.sip_to_investable_surplus_ratio === "number" || candidate.sip_to_investable_surplus_ratio === null
        ? candidate.sip_to_investable_surplus_ratio
        : undefined,
    reason_codes: Array.isArray(candidate.reason_codes) ? candidate.reason_codes.map((item) => String(item)) : undefined,
    suggested_sip: candidate.suggested_sip,
    suggestions: candidate.suggestions.map((item) => String(item)),
    auto_adjustment: candidate.auto_adjustment,
  };
}
