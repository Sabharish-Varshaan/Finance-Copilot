"use client";

import axios from "axios";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getProfile, upsertProfile } from "@/services/profileService";
import type { RiskProfile } from "@/types";

type FormState = {
  age: number;
  income: number;
  expenses: number;
  savings: number;
  loans: number;
  emi: number;
  risk_profile: RiskProfile;
  has_investments: boolean;
};

type FieldErrors = Partial<Record<keyof Omit<FormState, "risk_profile" | "has_investments">, string>>;

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [form, setForm] = useState<FormState>({
    age: 28,
    income: 120000,
    expenses: 50000,
    savings: 250000,
    loans: 0,
    emi: 0,
    risk_profile: "moderate" as RiskProfile,
    has_investments: false,
  });

  useEffect(() => {
    void (async () => {
      try {
        const existingProfile = await getProfile();
        setForm({
          age: existingProfile.age,
          income: existingProfile.income,
          expenses: existingProfile.expenses,
          savings: existingProfile.savings,
          loans: existingProfile.loans,
          emi: existingProfile.emi,
          risk_profile: existingProfile.risk_profile,
          has_investments: existingProfile.has_investments,
        });
      } catch {
        // No existing profile is fine for first-time onboarding.
      } finally {
        setLoadingProfile(false);
      }
    })();
  }, []);

  const parseNumberInput = (raw: string): number => {
    const normalized = raw.replace(/,/g, "").trim();
    if (!normalized) {
      return 0;
    }
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const setNumericField = (key: keyof Omit<FormState, "risk_profile" | "has_investments">, value: number) => {
    setForm((prev) => ({ ...prev, [key]: Number.isFinite(value) ? value : 0 }));
    setFieldErrors((prev) => ({ ...prev, [key]: "" }));
  };

  const validateForm = (): boolean => {
    const errors: FieldErrors = {};

    if (form.age < 18 || form.age > 100) {
      errors.age = "Age must be between 18 and 100.";
    }
    if (form.income <= 0) {
      errors.income = "Income must be greater than 0.";
    }
    if (form.expenses < 0) {
      errors.expenses = "Expenses cannot be negative.";
    }
    if (form.savings < 0) {
      errors.savings = "Savings cannot be negative.";
    }
    if (form.loans < 0) {
      errors.loans = "Loans cannot be negative.";
    }
    if (form.emi < 0) {
      errors.emi = "EMI cannot be negative.";
    }
    if (form.emi > form.income) {
      errors.emi = "EMI cannot be greater than income.";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!validateForm()) {
      toast.error("Please correct highlighted fields.");
      return;
    }

    try {
      setLoading(true);
      await upsertProfile(form);
      toast.success("Profile saved");
      router.push("/dashboard");
    } catch (error) {
      const detail = axios.isAxiosError(error)
        ? (error.response?.data?.detail ?? "Failed to save profile")
        : "Failed to save profile";
      toast.error(typeof detail === "string" ? detail : "Failed to save profile");
    } finally {
      setLoading(false);
    }
  };

  if (loadingProfile) {
    return (
      <main className="page-enter mx-auto w-full max-w-3xl px-4 py-10">
        <Card>
          <p className="text-sm text-muted">Loading your latest profile...</p>
        </Card>
      </main>
    );
  }

  return (
    <main className="page-enter mx-auto w-full max-w-3xl px-4 py-10">
      <Card>
        <p className="text-xs uppercase tracking-[0.18em] text-muted">Onboarding</p>
        <h1 className="mt-2 text-4xl font-semibold">Financial Profile Setup</h1>
        <p className="mt-1 text-sm text-muted">
          Enter clear monthly numbers so we can personalize your score and mentor advice.
        </p>

        <form className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={onSubmit}>
          <div>
            <label className="mb-1 block text-sm font-medium text-text">Age</label>
            <Input
              type="number"
              min={18}
              max={100}
              value={form.age}
              onChange={(e) => setNumericField("age", parseNumberInput(e.currentTarget.value))}
              placeholder="e.g. 28"
              required
            />
            {fieldErrors.age ? <p className="mt-1 text-xs text-danger">{fieldErrors.age}</p> : null}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-text">Monthly Income (INR)</label>
            <Input
              type="number"
              min={0}
              step="100"
              value={form.income}
              onChange={(e) => setNumericField("income", parseNumberInput(e.currentTarget.value))}
              placeholder="e.g. 120000"
              required
            />
            {fieldErrors.income ? <p className="mt-1 text-xs text-danger">{fieldErrors.income}</p> : null}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-text">Monthly Expenses (INR)</label>
            <Input
              type="number"
              min={0}
              step="100"
              value={form.expenses}
              onChange={(e) => setNumericField("expenses", parseNumberInput(e.currentTarget.value))}
              placeholder="e.g. 50000"
              required
            />
            {fieldErrors.expenses ? <p className="mt-1 text-xs text-danger">{fieldErrors.expenses}</p> : null}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-text">Total Savings (INR)</label>
            <Input
              type="number"
              min={0}
              step="100"
              value={form.savings}
              onChange={(e) => setNumericField("savings", parseNumberInput(e.currentTarget.value))}
              placeholder="e.g. 250000"
              required
            />
            {fieldErrors.savings ? <p className="mt-1 text-xs text-danger">{fieldErrors.savings}</p> : null}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-text">Outstanding Loans (INR)</label>
            <Input
              type="number"
              min={0}
              step="100"
              value={form.loans}
              onChange={(e) => setNumericField("loans", parseNumberInput(e.currentTarget.value))}
              placeholder="e.g. 400000"
              required
            />
            {fieldErrors.loans ? <p className="mt-1 text-xs text-danger">{fieldErrors.loans}</p> : null}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-text">Monthly EMI (INR)</label>
            <Input
              type="number"
              min={0}
              step="100"
              value={form.emi}
              onChange={(e) => setNumericField("emi", parseNumberInput(e.currentTarget.value))}
              placeholder="e.g. 15000"
              required
            />
            {fieldErrors.emi ? <p className="mt-1 text-xs text-danger">{fieldErrors.emi}</p> : null}
          </div>

          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium text-text">Risk Profile</label>
            <select
              className="w-full rounded-2xl border border-borderSoft bg-panelAlt/80 px-4 py-3 text-sm outline-none transition-all duration-300 ease-smooth focus:border-accent/60 focus:shadow-[0_0_0_4px_rgba(0,255,163,0.14)]"
              value={form.risk_profile}
              onChange={(e) => setForm({ ...form, risk_profile: e.target.value as RiskProfile })}
            >
              <option value="conservative">Conservative (lower risk)</option>
              <option value="moderate">Moderate (balanced)</option>
              <option value="aggressive">Aggressive (higher risk)</option>
            </select>
          </div>

          <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-panelAlt/65 p-3 text-sm text-muted sm:col-span-2">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[#00ffa3]"
              checked={form.has_investments}
              onChange={(e) => setForm({ ...form, has_investments: e.target.checked })}
            />
            I already have investments
          </label>

          <Button type="submit" className="sm:col-span-2" isLoading={loading}>
            Save and Continue
          </Button>
        </form>
      </Card>
    </main>
  );
}
