"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  createFirePlan,
  getFirePlanById,
  listFirePlanHistory,
  type FireGoalInput,
  type FirePlanHistoryItem,
  type FirePlanRecord,
  type FireProfileInput,
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

const defaultGoal: FireGoalInput = { name: "House", amount: 5000000, years: 10 };

export default function FirePlannerPage() {
  const [profile, setProfile] = useState<FireProfileInput>(defaultProfile);
  const [goals, setGoals] = useState<FireGoalInput[]>([defaultGoal]);
  const [result, setResult] = useState<FirePlanRecord | null>(null);
  const [retirementAge, setRetirementAge] = useState<number>(DEFAULT_RETIREMENT_AGE);
  const [multiplier, setMultiplier] = useState<number>(DEFAULT_MULTIPLIER);
  const [history, setHistory] = useState<FirePlanHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        setHistoryLoading(true);
        const rows = await listFirePlanHistory();
        setHistory(rows);
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
                onChange={(e) => setProfile((prev) => ({ ...prev, age: Number(e.currentTarget.value) || 0 }))}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Monthly Income (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.monthly_income}
                onChange={(e) =>
                  setProfile((prev) => ({ ...prev, monthly_income: Number(e.currentTarget.value) || 0 }))
                }
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Monthly Expenses (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.monthly_expenses}
                onChange={(e) =>
                  setProfile((prev) => ({ ...prev, monthly_expenses: Number(e.currentTarget.value) || 0 }))
                }
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Current Savings (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.current_savings}
                onChange={(e) =>
                  setProfile((prev) => ({ ...prev, current_savings: Number(e.currentTarget.value) || 0 }))
                }
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Current Insurance Coverage (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.insurance_coverage}
                onChange={(e) =>
                  setProfile((prev) => ({ ...prev, insurance_coverage: Number(e.currentTarget.value) || 0 }))
                }
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text">Monthly EMI (INR)</label>
              <Input
                type="number"
                min={0}
                value={profile.monthly_emi}
                onChange={(e) => setProfile((prev) => ({ ...prev, monthly_emi: Number(e.currentTarget.value) || 0 }))}
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
            <Card className="sm:col-span-2">
              <p className="text-sm font-medium text-text">Planning Assumptions</p>
              <div className="mt-2 grid grid-cols-1 gap-2 text-sm text-muted sm:grid-cols-3">
                <p>Inflation: <span className="text-text">6%</span></p>
                <p>Expected Return: <span className="text-text">12%</span></p>
                <p>Safety Buffer: <span className="text-text">20%</span></p>
              </div>
            </Card>

            <div className="sm:col-span-2">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-sm font-medium text-text">Goals</p>
                <Button type="button" className="bg-panelAlt text-text" onClick={addGoal}>
                  Add Goal
                </Button>
              </div>
              <div className="space-y-2">
                {goals.map((goal, index) => (
                  <div key={`${goal.name}-${index}`} className="grid grid-cols-1 gap-2 rounded-2xl border border-white/10 bg-panelAlt/60 p-3 sm:grid-cols-4">
                    <Input
                      placeholder="Goal name"
                      value={goal.name}
                      onChange={(e) => updateGoal(index, "name", e.currentTarget.value)}
                    />
                    <Input
                      type="number"
                      min={0}
                      placeholder="Target amount"
                      value={goal.amount}
                      onChange={(e) => updateGoal(index, "amount", e.currentTarget.value)}
                    />
                    <Input
                      type="number"
                      min={1}
                      placeholder="Years"
                      value={goal.years}
                      onChange={(e) => updateGoal(index, "years", e.currentTarget.value)}
                    />
                    <Button
                      type="button"
                      className="bg-danger text-white"
                      onClick={() => removeGoal(index)}
                      disabled={goals.length === 1}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
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
        <section className="mt-4 grid gap-4 md:grid-cols-2">
          <Card>
            <h3 className="text-xl font-semibold">FIRE Snapshot</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              <li>Target Corpus: <span className="text-text">{formatCurrency(result.fire_target)}</span></li>
              <li>Years to Retire: <span className="text-text">{result.years_to_retire}</span></li>
              <li>Retirement Age: <span className="text-text">{result.retirement_age}</span></li>
              <li>FIRE Multiplier: <span className="text-text">{result.multiplier.toFixed(1)}x</span></li>
              <li>Required SIP: <span className="text-text">{formatCurrency(result.monthly_sip_fire)}/month</span></li>
              <li>Emergency Gap: <span className="text-text">{result.emergency_gap ? "Yes" : "No"}</span></li>
              <li>Insurance Gap: <span className="text-text">{result.insurance_gap ? "Yes" : "No"}</span></li>
              <li>Goal SIP Total: <span className="text-text">{formatCurrency(totalGoalSip)}/month</span></li>
            </ul>
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

          <Card className="md:col-span-2">
            <h3 className="text-xl font-semibold">Goal-wise SIP</h3>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-muted">
                  <tr>
                    <th className="py-2">Goal</th>
                    <th className="py-2">Target</th>
                    <th className="py-2">Monthly SIP</th>
                  </tr>
                </thead>
                <tbody>
                  {result.goal_plan.map((goal) => (
                    <tr key={goal.name} className="border-t border-white/10">
                      <td className="py-2 text-text">{goal.name}</td>
                      <td className="py-2 text-text">{formatCurrency(goal.target)}</td>
                      <td className="py-2 text-text">{formatCurrency(goal.monthly_sip)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-sm text-muted">
              Total Goal SIP: <span className="text-text">{formatCurrency(totalGoalSip)}/month</span>
            </p>
          </Card>

          <Card className="md:col-span-2">
            <h3 className="text-xl font-semibold">Monthly Roadmap</h3>
            <p className="mt-1 text-sm text-muted">First 12 months followed by yearly milestones.</p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-muted">
                  <tr>
                    <th className="py-2">Month</th>
                    <th className="py-2">Estimated Corpus</th>
                  </tr>
                </thead>
                <tbody>
                  {result.monthly_plan.map((point) => (
                    <tr key={point.month} className="border-t border-white/10">
                      <td className="py-2 text-text">{point.month}</td>
                      <td className="py-2 text-text">{formatCurrency(point.corpus)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

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
      ) : null}
    </main>
  );
}
