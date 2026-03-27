import api from "@/services/api";

export interface FireProfileInput {
  age: number;
  monthly_income: number;
  monthly_expenses: number;
  current_savings: number;
  insurance_coverage: number;
  monthly_emi: number;
  risk_profile: string;
}

export interface FireGoalInput {
  name: string;
  amount: number;
  years: number;
}

export interface FireGoalPlan {
  name: string;
  target: number;
  monthly_sip: number;
}

export interface FirePlanRecord {
  id: number;
  fire_target: number;
  years_to_retire: number;
  monthly_sip_fire: number;
  goal_plan: FireGoalPlan[];
  monthly_plan: { month: number; corpus: number }[];
  allocation: { equity: number; debt: number };
  emergency_gap: boolean;
  insurance_gap: boolean;
  tax_suggestions: string[];
  recommendation_flags: string[];
  retirement_age: number;
  multiplier: number;
  created_at: string;
}

export interface FirePlanHistoryItem {
  id: number;
  fire_target: number;
  monthly_sip_fire: number;
  years_to_retire: number;
  created_at: string;
}

export interface FirePlanRequest {
  profile: FireProfileInput;
  goals: FireGoalInput[];
  retirement_age?: number;
  multiplier?: number;
}

export async function createFirePlan(payload: FirePlanRequest) {
  const response = await api.post<FirePlanRecord>("/fire-plan/create", payload);
  return response.data;
}

export async function listFirePlanHistory() {
  const response = await api.get<FirePlanHistoryItem[]>("/fire-plan/history");
  return response.data;
}

export async function getFirePlanById(planId: number) {
  const response = await api.get<FirePlanRecord>(`/fire-plan/${planId}`);
  return response.data;
}
