export type RiskProfile = "conservative" | "moderate" | "aggressive";

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface FinancialProfilePayload {
  age: number;
  income: number;
  expenses: number;
  savings: number;
  insurance_coverage: number;
  loans: number;
  emi: number;
  risk_profile: RiskProfile;
  has_investments: boolean;
}

export interface ComponentScores {
  emergency_fund: number;
  debt_ratio: number;
  savings_rate: number;
  investment_presence: number;
}

export interface ScoreBreakdown {
  emergency_fund_months: number;
  debt_ratio: number;
  savings_rate: number;
  investment_presence: boolean;
  component_scores: ComponentScores;
}

export interface MoneyHealthScore {
  score: number;
  grade: string;
  breakdown: ScoreBreakdown;
}

export interface Goal {
  id: number;
  user_id: number;
  category: string;
  title: string;
  target_amount: number;
  current_amount: number;
  expected_annual_return: number;
  target_date: string;
  monthly_sip_required: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  response: string;
}

export interface NudgeResponse {
  nudges: string[];
}
