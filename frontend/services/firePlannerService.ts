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
  target_amount_original?: number;
  target_amount_inflated?: number;
  inflation_impact?: number;
  monthly_sip: number;
  monthly_sip_required?: number;
  status?: "achievable" | "adjusted_plan" | "constrained" | "unrealistic" | string;
  status_description?: string;
  underfunded?: boolean;
  timeline_adjusted?: boolean;
  adjusted_years?: number | null;
}

export interface FireScenario {
  name: "current_sip" | "sip_plus_25" | "sip_minus_25" | string;
  sip: number;
  years_to_target: number | null;
  target_age: number | null;
  achieved_age?: number | null;
  original_target_age?: number | null;
  status: "achievable" | "unrealistic" | string;
}

export interface FirePreConditions {
  required_emergency_fund: number;
  current_emergency_fund: number;
  required_insurance: number;
  current_insurance: number;
  monthly_surplus: number;
}

export interface FireInvestmentBreakdownItem {
  type: string;
  amount: number;
}

export interface FireInvestmentAssetPlan {
  percentage: number;
  amount: number;
  breakdown: FireInvestmentBreakdownItem[];
}

export interface FireInvestmentPlan {
  total_investment: number;
  mode: "conservative" | "balanced" | "aggressive" | string;
  allocation: {
    equity: FireInvestmentAssetPlan;
    debt: FireInvestmentAssetPlan;
    gold: FireInvestmentAssetPlan;
  };
  explanation: string;
}

export interface FirePlanRecord {
  id: number;
  fire_target: number;
  years_to_retire: number;
  monthly_sip_fire: number;
  fire_sip?: number;
  goal_sip_total?: number;
  available_surplus?: number;
  remaining_surplus?: number;
  investable_surplus?: number;
  required_goal_sip?: number;
  goals_feasible?: boolean;
  allocation_split?: {
    fire_percentage: number;
    goal_percentage: number;
  };
  minimum_sip_required?: number;
  total_assets?: number;
  investment_breakdown?: {
    equity: number;
    debt: number;
    gold: number;
  };
  goal_plan: FireGoalPlan[];
  monthly_plan: { month: number; corpus: number }[];
  allocation: { equity: number; debt: number };
  emergency_gap: boolean;
  insurance_gap: boolean;
  tax_suggestions: string[];
  recommendation_flags: string[];
  retirement_age: number;
  multiplier: number;
  expected_return: number;
  return_source: "user" | "system";
  goal_status?: "achievable" | "needs_adjustment" | "unrealistic" | string;
  explanation?: string;
  risk_flags?: string[];
  scenarios?: FireScenario[];
  priority_order?: string[];
  priority_text?: string[];
  next_steps?: string[];
  investment_plan?: FireInvestmentPlan | null;
  pre_conditions?: FirePreConditions | null;
  timeline_adjusted?: boolean;
  adjusted_timeline_years?: number | null;
  new_target_date?: string | null;
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
  expected_return?: number;
  investment_mode?: "conservative" | "balanced" | "aggressive";
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

export async function getCurrentFirePlan() {
  try {
    const response = await api.get<FirePlanRecord>("/fire-plan/current");
    return response.data;
  } catch (error) {
    // No current plan exists
    return null;
  }
}
