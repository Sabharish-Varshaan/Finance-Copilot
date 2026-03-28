"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatCurrencyCompact, formatCurrencyWithHint } from "@/lib/utils";
import { getProfile } from "@/services/profileService";
import {
  createFirePlan,
  getCurrentFirePlan,
  getFirePlanById,
  listFirePlanHistory,
  type FireGoalInput,
  type FirePlanHistoryItem,
  type FirePlanRecord,
  type FireProfileInput,
  type FireScenario,
} from "@/services/firePlannerService";

const currency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function formatCurrency(value: number) {
  return currency.format(Number.isFinite(value) ? value : 0);
}

const defaultProfile: FireProfileInput = {
  age: 30,
  monthly_income: 100000,
  monthly_expenses: 50000,
  current_savings: 300000,
  insurance_coverage: 0,
  monthly_emi: 10000,
  risk_profile: "moderate",
};

const DEFAULT_RETIREMENT_AGE = 55;
const DEFAULT_MULTIPLIER = 33;

const FLAG_LABELS: Record<string, string> = {
  build_emergency_fund: "Build emergency fund first",
  reduce_debt: "Reduce debt burden before aggressive investing",
  increase_insurance: "Increase life and health insurance coverage",
};

const STATUS_META: Record<string, { label: string; className: string }> = {
  achievable: {
    label: "Achievable",
    className: "border border-success/50 bg-success/15 text-success",
  },
  needs_adjustment: {
    label: "Adjusted Plan (SIP reduced + timeline extended)",
    className: "border border-warning/60 bg-warning/15 text-warning",
  },
  adjusted_plan: {
    label: "Adjusted Plan (SIP reduced + timeline extended)",
    className: "border border-warning/60 bg-warning/15 text-warning",
  },
  unrealistic: {
    label: "Unrealistic",
    className: "border border-danger/60 bg-danger/15 text-danger",
  },
};

const RISK_FLAG_LABELS: Record<string, string> = {
  high_sip_dependency: "FIRE SIP is consuming a high share of your surplus",
  low_emergency_fund: "Emergency reserve is below 6 months of expenses",
  high_debt_pressure: "EMI burden is above the recommended limit",
};

const PRIORITY_LABELS: Record<string, string> = {
  build_emergency_fund: "Build emergency fund",
  reduce_high_interest_debt: "Reduce high-interest debt",
  increase_insurance_coverage: "Increase insurance coverage",
  invest_for_goals_and_fire: "Invest for goals and FIRE",
  establish_emergency_fund: "Build emergency fund",
  eliminate_high_debt: "Reduce high-interest debt",
  increase_life_insurance: "Increase insurance coverage",
  invest_in_fire_and_goals: "Invest for goals and FIRE",
};

const SCENARIO_LABELS: Record<string, string> = {
  current_sip: "Current SIP",
  sip_plus_25: "+25% SIP",
  sip_minus_25: "-25% SIP",
};

const defaultGoal: FireGoalInput = { name: "House", amount: 5000000, years: 10 };

export default function FirePlannerPage() {
  const [profile, setProfile] = useState<FireProfileInput>(defaultProfile);
  const [goals, setGoals] = useState<FireGoalInput[]>([defaultGoal]);
  const [result, setResult] = useState<FirePlanRecord | null>(null);
  const [retirementAge, setRetirementAge] = useState<number>(DEFAULT_RETIREMENT_AGE);
  const [multiplier, setMultiplier] = useState<number>(DEFAULT_MULTIPLIER);
  const [useDefaultReturn, setUseDefaultReturn] = useState(true);
  const [expectedReturnPct, setExpectedReturnPct] = useState<number>(10);
  const [history, setHistory] = useState<FirePlanHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  const monthYearLabel = (monthOffset: number, baseDate: Date): string => {
    const date = new Date(baseDate);
    date.setDate(1);
    date.setMonth(date.getMonth() + Math.max(monthOffset - 1, 0));
    return date.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
  };

  useEffect(() => {
    void (async () => {
      try {
        setHistoryLoading(true);
        try {
          const dbProfile = await getProfile();
          setProfile({
            age: Number(dbProfile.age) || defaultProfile.age,
            monthly_income: Number(dbProfile.income) || defaultProfile.monthly_income,
            monthly_expenses: Number(dbProfile.expenses) || defaultProfile.monthly_expenses,
            current_savings: Number(dbProfile.savings) || defaultProfile.current_savings,
            insurance_coverage: Number(dbProfile.insurance_coverage) || defaultProfile.insurance_coverage,
            monthly_emi: Number(dbProfile.emi) || defaultProfile.monthly_emi,
            risk_profile: dbProfile.risk_profile || defaultProfile.risk_profile,
          });
        } catch {
          // Keep local defaults when profile is not yet created.
        }

        const rows = await listFirePlanHistory();
        setHistory(rows);
        
        // PHASE 6.4: Auto-load current plan on mount
        if (rows.length > 0) {
          try {
            const currentPlan = await getCurrentFirePlan();
            if (currentPlan) {
              setResult(currentPlan);
            }
          } catch {
            // No current plan or error loading it
          }
        }
      } catch {
        // history may be empty for first-time users
      } finally {
        setHistoryLoading(false);
      }
    })();
  }, []);

  const totalGoalSip = useMemo(
    () => (result ? result.goal_plan.reduce((sum, goal) => sum + goal.monthly_sip, 0) : 0),
    [result],
  );

  const monthlySurplus = useMemo(
    () => Math.max(profile.monthly_income - profile.monthly_expenses - profile.monthly_emi, 0),
    [profile.monthly_emi, profile.monthly_expenses, profile.monthly_income],
  );

  const totalRecommendedSip = useMemo(() => {
    if (!result) return 0;
    return result.monthly_sip_fire + totalGoalSip;
  }, [result, totalGoalSip]);

  const sipPressure = useMemo(() => {
    if (!profile.monthly_income) return 0;
    return (totalRecommendedSip / profile.monthly_income) * 100;
  }, [profile.monthly_income, totalRecommendedSip]);

  const goalStatus = result?.goal_status ?? "achievable";
  const statusMeta = STATUS_META[goalStatus] ?? STATUS_META.achievable;
  const achievedRetirementAge = profile.age + (result?.years_to_retire ?? 0);

  const chartData = useMemo(
    () => {
      if (!result) return [];
      const baseDate = result.created_at ? new Date(result.created_at) : new Date();
      return (result.monthly_plan ?? []).map((point) => ({
        month: point.month,
        label: monthYearLabel(point.month, baseDate),
        corpus: point.corpus,
      }));
    },
    [result],
  );

  const scenarioCards = useMemo<FireScenario[]>(() => result?.scenarios ?? [], [result?.scenarios]);

  const priorityText = useMemo(() => {
    if (!result) return [];
    if ((result.priority_text ?? []).length > 0) return result.priority_text ?? [];
    return (result.priority_order ?? []).map((step) => PRIORITY_LABELS[step] ?? step);
  }, [result]);

  const nextSteps = useMemo(() => {
    if (!result) return [];
    if ((result.next_steps ?? []).length > 0) return result.next_steps ?? [];
    const fallback: string[] = [];
    if (result.emergency_gap) {
      fallback.push("Build emergency fund before increasing risk");
    }
    if (result.insurance_gap) {
      const recommendedInsurance = result.pre_conditions?.required_insurance ?? 0;
      fallback.push(`Get life insurance (${formatCurrency(recommendedInsurance)} recommended)`);
    }
    fallback.push(`Invest ${formatCurrency(result.monthly_sip_fire)}/month consistently`);
    fallback.push("Increase SIP gradually");
    return fallback.slice(0, 3);
  }, [result]);

  const updateGoal = (index: number, field: keyof FireGoalInput, value: string) => {
    setGoals((prev) =>
      prev.map((goal, idx) => {
        if (idx !== index) return goal;
        if (field === "name") return { ...goal, name: value };
        return { ...goal, [field]: Number(value) || 0 };
      }),
    );
  };

  const addGoal = () => {
    setGoals((prev) => [...prev, { name: "", amount: 0, years: 1 }]);
  };

  const removeGoal = (index: number) => {
    setGoals((prev) => prev.filter((_, idx) => idx !== index));
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const validGoals = goals.filter((goal) => goal.name.trim() && goal.amount > 0 && goal.years > 0);
    if (!validGoals.length) {
      toast.error("Add at least one valid goal.");
      return;
    }

    try {
      setLoading(true);
      const plan = await createFirePlan({
        profile,
        goals: validGoals,
        retirement_age: retirementAge,
        multiplier,
        expected_return: useDefaultReturn ? undefined : expectedReturnPct / 100,
      });
      setResult(plan);
      setHistory((prev) => [
        {
          id: plan.id,
          fire_target: plan.fire_target,
          monthly_sip_fire: plan.monthly_sip_fire,
          years_to_retire: plan.years_to_retire,
          created_at: plan.created_at,
        },
        ...prev.filter((item) => item.id !== plan.id),
      ]);
      toast.success("FIRE plan generated");
    } catch {
      toast.error("Could not generate FIRE plan");
    } finally {
      setLoading(false);
    }
  };

  const loadHistoryDetail = async (planId: number) => {
    try {
      const detail = await getFirePlanById(planId);
      setResult(detail);
    } catch {
      toast.error("Could not load selected FIRE plan");
    }
  };

  return (
    <main className="page-enter mx-auto w-full max-w-6xl px-4 py-10">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight">FIRE Planner</h1>
          <p className="mt-1 text-sm text-muted">
            Build your Financial Independence roadmap with goal-wise SIP allocation.
          </p>
        </div>
        <Link href="/dashboard">
          <Button className="border border-white/10 bg-panelAlt text-text shadow-none">Back to Dashboard</Button>
        </Link>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={onSubmit}>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Age</label>
              <Input
                type="number"
                min={18}
                max={100}
                value={profile.age}
                onChange={(e) => {
                  const age = Number(e.target.value) || 0;
                  setProfile((prev) => ({ ...prev, age }));
                }}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Monthly Income (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.monthly_income}
                onChange={(e) => {
                  const monthlyIncome = Number(e.target.value) || 0;
                  setProfile((prev) => ({ ...prev, monthly_income: monthlyIncome }));
                }}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Monthly Expenses (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.monthly_expenses}
                onChange={(e) => {
                  const monthlyExpenses = Number(e.target.value) || 0;
                  setProfile((prev) => ({ ...prev, monthly_expenses: monthlyExpenses }));
                }}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Current Savings (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.current_savings}
                onChange={(e) => {
                  const currentSavings = Number(e.target.value) || 0;
                  setProfile((prev) => ({ ...prev, current_savings: currentSavings }));
                }}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Current Insurance Coverage (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.insurance_coverage}
                onChange={(e) => {
                  const insuranceCoverage = Number(e.target.value) || 0;
                  setProfile((prev) => ({ ...prev, insurance_coverage: insuranceCoverage }));
                }}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Monthly EMI (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.monthly_emi}
                onChange={(e) => {
                  const monthlyEmi = Number(e.target.value) || 0;
                  setProfile((prev) => ({ ...prev, monthly_emi: monthlyEmi }));
                }}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Risk Profile</label>
              <select
                className="w-full rounded-2xl border border-borderSoft bg-panelAlt/80 px-4 py-3 text-sm text-text outline-none transition-all duration-300 ease-smooth focus:border-accent/60 focus:shadow-[0_0_0_4px_rgba(0,255,163,0.14)]"
                value={profile.risk_profile}
                onChange={(e) => setProfile((prev) => ({ ...prev, risk_profile: e.target.value }))}
              >
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Retirement Age</label>
              <Input
                type="number"
                min={40}
                max={75}
                value={retirementAge}
                onChange={(e) => setRetirementAge(Number(e.currentTarget.value) || DEFAULT_RETIREMENT_AGE)}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">FIRE Multiplier</label>
              <Input
                type="number"
                min={25}
                max={50}
                value={multiplier}
                onChange={(e) => setMultiplier(Number(e.currentTarget.value) || DEFAULT_MULTIPLIER)}
                required
              />
              <div className="mt-2 flex gap-2">
                <Button type="button" className="bg-panelAlt text-text" onClick={() => setMultiplier(28)}>
                  Lean
                </Button>
                <Button type="button" className="bg-panelAlt text-text" onClick={() => setMultiplier(33)}>
                  Standard
                </Button>
                <Button type="button" className="bg-panelAlt text-text" onClick={() => setMultiplier(40)}>
                  Safe
                </Button>
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Expected Return (%)</label>
              <Input
                type="number"
                min={5}
                max={15}
                step={0.1}
                value={expectedReturnPct}
                disabled={useDefaultReturn}
                onChange={(e) => setExpectedReturnPct(Number(e.currentTarget.value) || 10)}
              />
              <label className="mt-2 inline-flex items-center gap-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={useDefaultReturn}
                  onChange={(e) => setUseDefaultReturn(e.currentTarget.checked)}
                />
                Use default (recommended)
              </label>
              <p className="mt-2 text-xs text-muted">Typical returns: Low: 6-7% | Moderate: 8-10% | High: 10-12%</p>
              {!useDefaultReturn && expectedReturnPct > 12 ? (
                <p className="mt-1 text-xs text-warning">High return assumptions may be unrealistic</p>
              ) : null}
            </div>
            <Card className="sm:col-span-2">
              <p className="text-sm font-medium text-text">Planning Assumptions</p>
              <div className="mt-2 grid grid-cols-1 gap-2 text-sm text-muted sm:grid-cols-3">
                <p>Inflation: <span className="text-text">6%</span></p>
                <p>
                  Expected Return: <span className="text-text">{result ? `${(result.expected_return * 100).toFixed(1)}%` : "Risk-based default"}</span>
                </p>
                <p>Safety Buffer: <span className="text-text">Not applied</span></p>
              </div>
            </Card>

            <div className="sm:col-span-2">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-text">Financial Goals</p>
                  <p className="mt-1 text-xs text-muted">Add specific targets like house purchase, education, wedding, etc. These will be prioritized after FIRE with goal-specific SIP allocation.</p>
                </div>
                <Button type="button" className="bg-accent text-background hover:bg-accent/90" onClick={addGoal}>
                  + Add Goal
                </Button>
              </div>
              <div className="space-y-3">
                {goals.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted">No goals added yet. Click "Add Goal" to start planning.</p>
                ) : (
                  goals.map((goal, index) => (
                    <div key={index} className="rounded-2xl border border-white/10 bg-panelAlt/60 p-4">
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-12">
                        <div className="sm:col-span-4">
                          <label className="mb-1 block text-xs font-medium text-muted">Goal Name</label>
                          <Input
                            placeholder="e.g., House down payment"
                            value={goal.name}
                            onChange={(e) => updateGoal(index, "name", e.currentTarget.value)}
                          />
                        </div>
                        <div className="sm:col-span-4">
                          <label className="mb-1 block text-xs font-medium text-muted">Target Amount (INR)</label>
                          <Input
                            type="number"
                            min={0}
                            placeholder="0"
                            value={goal.amount}
                            onChange={(e) => updateGoal(index, "amount", e.currentTarget.value)}
                          />
                          <p className="mt-1 text-xs text-muted/70">Inflation-adjusted by planner</p>
                        </div>
                        <div className="sm:col-span-3">
                          <label className="mb-1 block text-xs font-medium text-muted">Timeline (Years)</label>
                          <Input
                            type="number"
                            min={1}
                            placeholder="1"
                            value={goal.years}
                            onChange={(e) => updateGoal(index, "years", e.currentTarget.value)}
                          />
                        </div>
                        <div className="flex items-end sm:col-span-1">
                          <Button
                            type="button"
                            className="w-full bg-danger/20 text-danger hover:bg-danger/30"
                            onClick={() => removeGoal(index)}
                            disabled={goals.length === 1}
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <Button className="sm:col-span-2" type="submit" isLoading={loading}>
              Generate FIRE Plan
            </Button>
          </form>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold">Plan History</h2>
          {historyLoading ? <p className="mt-2 text-sm text-muted">Loading...</p> : null}
          <div className="mt-3 space-y-2">
            {history.length ? (
              history.map((item) => (
                <button
                  key={item.id}
                  className="w-full rounded-xl border border-white/10 bg-panelAlt/60 p-3 text-left text-sm transition hover:border-accent/50"
                  onClick={() => loadHistoryDetail(item.id)}
                >
                  <p className="font-medium text-text">{formatCurrency(item.fire_target)}</p>
                  <p className="text-muted">SIP {formatCurrency(item.monthly_sip_fire)}/mo</p>
                  <p className="text-xs text-muted/80">
                    {new Date(item.created_at).toLocaleDateString()} - {item.years_to_retire} years to retire
                  </p>
                </button>
              ))
            ) : (
              <p className="text-sm text-muted">No plans yet.</p>
            )}
          </div>
        </Card>
      </div>

      {result ? (
        <>
          <section className="mt-4">
            <Card className="border-accent/30 bg-gradient-to-br from-accent/10 to-transparent">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted">Monthly Investment</p>
                  <p className="mt-2 text-2xl font-semibold text-accent">
                    {formatCurrencyWithHint(result.monthly_sip_fire + totalGoalSip)}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    FIRE: {formatCurrency(result.monthly_sip_fire)}
                    {totalGoalSip > 0 ? ` + Goals: ${formatCurrency(totalGoalSip)}` : ""}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted">Target Retirement</p>
                  <p className="mt-2 text-2xl font-semibold text-accent">
                    {formatCurrency(result.fire_target)}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    in {result.years_to_retire} years (Age {result.retirement_age})
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    You planned retirement at age {result.retirement_age}, but current plan achieves at age {achievedRetirementAge}.
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted">Plan Status</p>
                  <p className={`mt-2 text-lg font-semibold ${
                    goalStatus === "achievable"
                      ? "text-success"
                      : goalStatus === "needs_adjustment" || goalStatus === "adjusted_plan"
                      ? "text-warning"
                      : "text-danger"
                  }`}>
                    {statusMeta.label}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    {goalStatus === "achievable" && "✓ Fully achievable with current inputs"}
                    {(goalStatus === "needs_adjustment" || goalStatus === "adjusted_plan") &&
                      "⚠️ Adjusted Plan (SIP reduced + timeline extended)"}
                    {goalStatus === "unrealistic" && "✗ Not achievable within planning horizon"}
                  </p>
                </div>
              </div>
            </Card>
          </section>

          <section className="mt-4 grid gap-4 md:grid-cols-2">
          <Card>
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-xl font-semibold">FIRE Snapshot</h3>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusMeta.className}`}>
                {statusMeta.label}
              </span>
            </div>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              <li>Target Corpus: <span className="text-text">{formatCurrency(result.fire_target)}</span></li>
              <li>Years to Retire: <span className="text-text">{result.years_to_retire}</span></li>
              <li>Retirement Age: <span className="text-text">{result.retirement_age}</span></li>
              <li>FIRE Multiplier: <span className="text-text">{result.multiplier.toFixed(1)}x</span></li>
              
              {goalStatus === "unrealistic" ? (
                <>
                  <li>Current Proposed SIP: <span className="text-warning">{formatCurrency(result.monthly_sip_fire)}/month</span></li>
                  <li>Minimum SIP Needed: <span className="text-danger font-medium">{formatCurrency(result.minimum_sip_required ?? result.monthly_sip_fire)}/month</span></li>
                  <li className="text-xs text-danger/80">SIP shortfall: <span className="font-semibold">{formatCurrency((result.minimum_sip_required ?? 0) - result.monthly_sip_fire)}/month</span></li>
                </>
              ) : (
                <li>Required SIP: <span className="text-text">{formatCurrency(result.monthly_sip_fire)}/month</span></li>
              )}
              
              <li>Emergency Gap: <span className="text-text">{result.emergency_gap ? "Yes" : "No"}</span></li>
              <li>Insurance Gap: <span className="text-text">{result.insurance_gap ? "Yes" : "No"}</span></li>
              <li>Goal SIP Total: <span className="text-text">{formatCurrency(totalGoalSip)}/month</span></li>
              <li>
                Expected Return Used: <span className="text-text">{(result.expected_return * 100).toFixed(1)}% ({result.return_source === "user" ? "User selected" : "System default"})</span>
              </li>
              {result.timeline_adjusted ? (
                <li>
                  Adjusted Timeline: <span className="text-text">{result.adjusted_timeline_years ?? result.years_to_retire} years</span>
                  {result.new_target_date ? <span className="text-muted"> (target date {new Date(result.new_target_date).toLocaleDateString()})</span> : null}
                </li>
              ) : null}
            </ul>
            {result.explanation ? (
              <div className={`mt-3 rounded-xl border p-3 text-sm ${
                goalStatus === "unrealistic" 
                  ? "border-danger/40 bg-danger/10 text-danger"
                  : "border-white/10 bg-panelAlt/60 text-muted"
              }`}>
                <p className="font-medium text-text">Planner Explanation</p>
                <p className="mt-1 whitespace-pre-line">{result.explanation}</p>
              </div>
            ) : null}
            {result.recommendation_flags.length ? (
              <div className="mt-3 rounded-xl border border-warning/40 bg-warning/10 p-3 text-sm text-text">
                <p className="font-medium">Priority Actions</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-muted">
                  {result.recommendation_flags.map((flag) => (
                    <li key={flag}>{FLAG_LABELS[flag] ?? flag}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </Card>

          <Card>
            <h3 className="text-xl font-semibold">Allocation & Affordability</h3>
            <p className="mt-2 text-sm text-muted">
              Equity {result.allocation.equity}% | Debt {result.allocation.debt}%
            </p>
            <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-panelAlt">
              <div className="h-full bg-accent" style={{ width: `${result.allocation.equity}%` }} />
            </div>
            <div className="mt-4 space-y-1 text-sm text-muted">
              <p>
                Available Monthly Surplus: <span className="text-text">{formatCurrency(monthlySurplus)}</span>
              </p>
              <p>
                Recommended Total SIP: <span className="text-text">{formatCurrency(totalRecommendedSip)}</span>
              </p>
              <p>
                SIP Pressure: <span className="text-text">{sipPressure.toFixed(1)}%</span> of income
              </p>
            </div>
          </Card>

          {(result.risk_flags?.length ?? 0) > 0 ? (
            <Card className="md:col-span-2">
              <h3 className="text-xl font-semibold">Risk Warnings</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
                {(result.risk_flags ?? []).map((flag) => (
                  <li key={flag}>{RISK_FLAG_LABELS[flag] ?? flag}</li>
                ))}
              </ul>
            </Card>
          ) : null}

          {nextSteps.length > 0 ? (
            <Card className="md:col-span-2">
              <h3 className="text-xl font-semibold">What should you do next?</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
                {nextSteps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </Card>
          ) : null}

          <Card className="md:col-span-2">
            <h3 className="text-xl font-semibold">Execution Priorities</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-muted">
              {priorityText.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            {result.pre_conditions ? (
              <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-muted sm:grid-cols-2">
                <p>
                  Emergency Fund Target: <span className="text-text">{formatCurrency(result.pre_conditions.required_emergency_fund)}</span>
                </p>
                <p>
                  Current Emergency Fund: <span className="text-text">{formatCurrency(result.pre_conditions.current_emergency_fund)}</span>
                </p>
              <p className="mt-2 text-xs text-muted">Safety buffer is disabled for more aggressive planning.</p>
                <p>
                  Insurance Needed: <span className="text-text">{formatCurrency(result.pre_conditions.required_insurance)}</span>
                </p>
                <p>
                  Current Insurance: <span className="text-text">{formatCurrency(result.pre_conditions.current_insurance)}</span>
                </p>
                <p className="sm:col-span-2 text-xs text-muted">
                  Insurance recommendation is based on 10-12x annual income rule.
                </p>
              </div>
            ) : null}
          </Card>

          {(scenarioCards.length ?? 0) > 0 && goalStatus !== "unrealistic" ? (
            <Card className="md:col-span-2">
              <h3 className="text-xl font-semibold">Scenario Comparison</h3>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                {scenarioCards.map((scenario) => (
                  <div key={scenario.name} className="rounded-xl border border-white/10 bg-panelAlt/50 p-3">
                    <p className="text-sm font-semibold text-text">{SCENARIO_LABELS[scenario.name] ?? scenario.name}</p>
                    <p className="mt-1 text-sm text-muted">SIP: <span className="text-text">{formatCurrency(scenario.sip)}</span></p>
                    <p className="mt-1 text-sm text-muted">
                      Timeline: <span className="text-text">{scenario.years_to_target ? `${scenario.years_to_target} years` : "Not achievable"}</span>
                    </p>
                    {scenario.target_age ? (
                      <p className="mt-1 text-sm text-muted">
                        Achieved at age <span className="text-text">{scenario.achieved_age ?? scenario.target_age}</span>
                        <span className="text-muted"> (original target {scenario.original_target_age ?? result.retirement_age})</span>
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </Card>
          ) : goalStatus === "unrealistic" ? (
            <Card className="md:col-span-2">
              <div className="rounded-xl border border-danger/40 bg-danger/10 p-4">
                <p className="text-sm text-danger">
                  <span className="font-semibold">⚠️ Scenario Analysis Not Available:</span> This FIRE target cannot be achieved within the planning horizon. Scenario analysis is only provided for feasible goals.
                </p>
              </div>
            </Card>
          ) : null}

          <Card className="md:col-span-2">
            <h3 className="text-xl font-semibold">Goal-wise SIP</h3>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-muted">
                  <tr>
                    <th className="py-2">Goal</th>
                    <th className="py-2">Target</th>
                    <th className="py-2">Monthly SIP</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {result.goal_plan.map((goal) => (
                    <tr key={goal.name} className="border-t border-white/10">
                      <td className="py-2 text-text">{goal.name}</td>
                      <td className="py-2 text-text">
                        {formatCurrency(goal.target_amount_original ?? goal.target)} {"→"} {formatCurrency(goal.target_amount_inflated ?? goal.target)}
                        <p className="text-xs text-muted">{formatCurrencyCompact(goal.target_amount_original ?? goal.target)} → {formatCurrencyCompact(goal.target_amount_inflated ?? goal.target)} (inflation-adjusted)</p>
                      </td>
                      <td className="py-2 text-text">
                        {formatCurrency(goal.monthly_sip)}
                        {goal.underfunded ? (
                          <p className="text-xs text-warning">Very low contribution — consider increasing SIP</p>
                        ) : null}
                      </td>
                      <td className="py-2 text-text">
                        {goal.status === "adjusted_plan" || goal.status === "constrained"
                          ? "Adjusted Plan (SIP reduced + timeline extended)"
                          : goal.status === "unrealistic"
                          ? "Unrealistic"
                          : "Achievable"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-sm text-muted">
              Total Goal SIP: <span className="text-text">{formatCurrency(totalGoalSip)}/month</span>
            </p>
          </Card>

          {goalStatus !== "unrealistic" ? (
            <Card className="md:col-span-2">
              <h3 className="text-xl font-semibold">Monthly Roadmap</h3>
              <p className="mt-1 text-sm text-muted">First 12 months followed by yearly milestones.</p>

              <div className="mt-4 h-[280px] w-full rounded-xl border border-white/10 bg-panelAlt/40 p-2">
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <XAxis dataKey="label" stroke="#9ca3af" tickLine={false} axisLine={false} />
                      <YAxis
                        stroke="#9ca3af"
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value: number | string) => `${Math.round(Number(value) / 100000)}L`}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#0f1524",
                          border: "1px solid rgba(255,255,255,0.1)",
                          borderRadius: 12,
                        }}
                        formatter={(value: number) => formatCurrency(Number(value))}
                      />
                      <Line
                        type="monotone"
                        dataKey="corpus"
                        stroke="#00ffa3"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="px-3 py-4 text-sm text-muted">No roadmap data available for chart.</p>
                )}
              </div>

              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-muted">
                    <tr>
                      <th className="py-2">Month / Year</th>
                      <th className="py-2">Estimated Corpus</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.monthly_plan.map((point) => (
                      <tr key={point.month} className="border-t border-white/10">
                        <td className="py-2 text-text">
                          {monthYearLabel(point.month, result.created_at ? new Date(result.created_at) : new Date())}
                        </td>
                        <td className="py-2 text-text">{formatCurrency(point.corpus)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {result.monthly_plan.length > 0 && result.monthly_plan[result.monthly_plan.length - 1].corpus > result.fire_target ? (
                <p className="mt-3 text-xs text-muted">Final corpus exceeds target slightly due to compounding growth.</p>
              ) : null}
            </Card>
          ) : (
            <Card className="md:col-span-2">
              <div className="rounded-xl border border-danger/40 bg-danger/10 p-4">
                <p className="text-sm text-danger">
                  <span className="font-semibold">📊 Monthly Roadmap Not Generated:</span> A detailed roadmap is only generated for achievable FIRE goals. To see a roadmap, you'll need to either increase your monthly savings, reduce your FIRE target, or extend your timeline.
                </p>
              </div>
            </Card>
          )}

          {result.tax_suggestions.length ? (
            <Card className="md:col-span-2">
              <h3 className="text-xl font-semibold">Tax Suggestions</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
                {result.tax_suggestions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Card>
          ) : null}
        </section>
        </>
      ) : null}
    </main>
  );
}
