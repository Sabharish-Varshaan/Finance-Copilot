import { FormEvent, useMemo, useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FeasibilityModal } from "@/components/ui/feasibility-modal";
import { Input } from "@/components/ui/input";
import { currency } from "@/lib/utils";
import {
  extractGoalFeasibilityError,
  type GoalCreatePayload,
  type GoalCreateResponse,
  type GoalFeasibilityError,
  type GoalPlanningSummary,
  type GoalStatusFilter,
  type GoalUpdatePayload,
} from "@/services/goalService";
import type { Goal } from "@/types";

interface GoalListProps {
  goals: Goal[];
  selectedStatus: GoalStatusFilter;
  isLoading: boolean;
  onStatusChange: (status: GoalStatusFilter) => Promise<void>;
  onCreateGoal: (payload: GoalCreatePayload) => Promise<GoalCreateResponse>;
  onUpdateGoal: (goalId: number, payload: GoalUpdatePayload) => Promise<void>;
  onDeleteGoal: (goalId: number) => Promise<void>;
}

type RiskLevel = "conservative" | "moderate" | "aggressive";

const STATUS_TABS: GoalStatusFilter[] = ["active", "paused", "completed", "all"];
const CATEGORY_OPTIONS = ["retirement", "house", "travel", "education", "other"];

function riskToAnnualReturn(risk: RiskLevel) {
  if (risk === "conservative") return 0.08;
  if (risk === "aggressive") return 0.15;
  return 0.12;
}

function annualReturnToRisk(value: number): RiskLevel {
  if (value <= 0.09) return "conservative";
  if (value >= 0.14) return "aggressive";
  return "moderate";
}

function titleCase(input: string) {
  return input.charAt(0).toUpperCase() + input.slice(1);
}

export function GoalList({
  goals,
  selectedStatus,
  isLoading,
  onStatusChange,
  onCreateGoal,
  onUpdateGoal,
  onDeleteGoal,
}: GoalListProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [editingGoalId, setEditingGoalId] = useState<number | null>(null);
  const [busyGoalId, setBusyGoalId] = useState<number | null>(null);
  const [statusBusy, setStatusBusy] = useState<GoalStatusFilter | null>(null);
  const [applyingAutoAdjust, setApplyingAutoAdjust] = useState(false);
  const [feasibilityError, setFeasibilityError] = useState<GoalFeasibilityError | null>(null);
  const [lastPlanSummary, setLastPlanSummary] = useState<GoalPlanningSummary | null>(null);

  const [createForm, setCreateForm] = useState({
    category: "house",
    title: "",
    targetAmount: "",
    targetDate: "",
    riskLevel: "moderate" as RiskLevel,
    smartAdjust: true,
  });

  const [editForm, setEditForm] = useState({
    title: "",
    targetAmount: "",
    targetDate: "",
    riskLevel: "moderate" as RiskLevel,
    monthlySipOverride: "",
  });

  const selectedStatusLabel = useMemo(() => titleCase(selectedStatus), [selectedStatus]);

  const startEdit = (goal: Goal) => {
    setEditingGoalId(goal.id);
    setEditForm({
      title: goal.title,
      targetAmount: String(goal.target_amount),
      targetDate: goal.target_date.slice(0, 10),
      riskLevel: annualReturnToRisk(goal.expected_annual_return),
      monthlySipOverride: "",
    });
  };

  const onCreateSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const targetAmount = Number(createForm.targetAmount);
    if (!createForm.title.trim() || !createForm.targetDate || targetAmount <= 0) {
      return;
    }

    setIsCreating(true);
    try {
      const result = await onCreateGoal({
        category: createForm.category,
        title: createForm.title.trim(),
        target_amount: targetAmount,
        current_amount: 0,
        target_date: createForm.targetDate,
        expected_annual_return: riskToAnnualReturn(createForm.riskLevel),
        smart_adjust: createForm.smartAdjust,
      });
      setLastPlanSummary(result.planning);
      setCreateForm({
        category: "house",
        title: "",
        targetAmount: "",
        targetDate: "",
        riskLevel: "moderate",
        smartAdjust: true,
      });
      setFeasibilityError(null);
      if (result.planning.adjusted) {
        toast.success(`Goal adjusted and created at ${currency(result.planning.final_sip)}/month`);
      } else {
        toast.success("Goal created");
      }
    } catch (error) {
      const parsed = extractGoalFeasibilityError(error);
      if (parsed) {
        setFeasibilityError(parsed);
        return;
      }
      toast.error("Could not create goal");
    } finally {
      setIsCreating(false);
    }
  };

  const handleApplyAutoAdjust = async () => {
    if (!feasibilityError?.auto_adjustment) {
      return;
    }

    const targetAmount = Number(createForm.targetAmount);
    if (!createForm.title.trim() || !createForm.targetDate || targetAmount <= 0) {
      return;
    }

    setApplyingAutoAdjust(true);
    try {
      const result = await onCreateGoal({
        category: createForm.category,
        title: createForm.title.trim(),
        target_amount: targetAmount,
        current_amount: 0,
        target_date: feasibilityError.auto_adjustment.adjusted_target_date,
        expected_annual_return: riskToAnnualReturn(createForm.riskLevel),
        smart_adjust: false,
      });
      setLastPlanSummary(result.planning);

      setCreateForm({
        category: "house",
        title: "",
        targetAmount: "",
        targetDate: "",
        riskLevel: "moderate",
        smartAdjust: true,
      });
      setFeasibilityError(null);
      toast.success("Goal auto-adjusted and created");
    } catch {
      toast.error("Could not auto-adjust goal");
    } finally {
      setApplyingAutoAdjust(false);
    }
  };

  const onSaveEdit = async (goalId: number) => {
    const targetAmount = Number(editForm.targetAmount);
    if (!editForm.title.trim() || !editForm.targetDate || targetAmount <= 0) {
      return;
    }

    setBusyGoalId(goalId);
    try {
      const payload: GoalUpdatePayload = {
        title: editForm.title.trim(),
        target_amount: targetAmount,
        target_date: editForm.targetDate,
        expected_annual_return: riskToAnnualReturn(editForm.riskLevel),
      };

      if (editForm.monthlySipOverride.trim() !== "") {
        payload.monthly_sip_required = Number(editForm.monthlySipOverride);
      }

      await onUpdateGoal(goalId, payload);
      setEditingGoalId(null);
    } finally {
      setBusyGoalId(null);
    }
  };

  const updateGoalStatus = async (goalId: number, status: "active" | "paused" | "completed") => {
    setBusyGoalId(goalId);
    try {
      await onUpdateGoal(goalId, { status });
    } finally {
      setBusyGoalId(null);
    }
  };

  const deleteWithConfirm = async (goalId: number, title: string) => {
    const isConfirmed = window.confirm(`Delete goal \"${title}\"? This cannot be undone.`);
    if (!isConfirmed) return;

    setBusyGoalId(goalId);
    try {
      await onDeleteGoal(goalId);
      if (editingGoalId === goalId) {
        setEditingGoalId(null);
      }
    } finally {
      setBusyGoalId(null);
    }
  };

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold">Goals</h3>
          <p className="mt-1 text-sm text-muted">Create, edit, and manage goal lifecycle from one place.</p>
        </div>
        <span className="rounded-full border border-white/10 bg-panelAlt px-3 py-1 text-xs text-muted">
          Showing: {selectedStatusLabel}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {STATUS_TABS.map((tab) => (
          <Button
            key={tab}
            type="button"
            className={
              selectedStatus === tab
                ? "bg-accent text-[#05110d]"
                : "border border-white/10 bg-panelAlt text-text shadow-none"
            }
            disabled={statusBusy !== null}
            onClick={async () => {
              if (selectedStatus === tab) return;
              setStatusBusy(tab);
              try {
                await onStatusChange(tab);
              } finally {
                setStatusBusy(null);
              }
            }}
          >
            {titleCase(tab)}
          </Button>
        ))}
      </div>

      <form className="mt-5 grid gap-2 rounded-2xl border border-white/10 bg-panelAlt/65 p-3 sm:grid-cols-6" onSubmit={onCreateSubmit}>
        <Input
          className="sm:col-span-2"
          placeholder="Goal title"
          value={createForm.title}
          onChange={(event) => {
            const value = event.currentTarget.value;
            setCreateForm((prev) => ({ ...prev, title: value }));
          }}
          required
        />
        <Input
          type="number"
          className="sm:col-span-1"
          placeholder="Target amount"
          min={1}
          value={createForm.targetAmount}
          onChange={(event) => {
            const value = event.currentTarget.value;
            setCreateForm((prev) => ({ ...prev, targetAmount: value }));
          }}
          required
        />
        <Input
          type="date"
          className="sm:col-span-1"
          value={createForm.targetDate}
          onChange={(event) => {
            const value = event.currentTarget.value;
            setCreateForm((prev) => ({ ...prev, targetDate: value }));
          }}
          required
        />
        <select
          className="w-full rounded-2xl border border-borderSoft bg-panelAlt/80 px-4 py-3 text-sm text-text outline-none transition-all duration-300 ease-smooth focus:border-accent/60 focus:shadow-[0_0_0_4px_rgba(0,255,163,0.14)] sm:col-span-1"
          value={createForm.category}
          onChange={(event) => {
            const value = event.currentTarget.value;
            setCreateForm((prev) => ({ ...prev, category: value }));
          }}
        >
          {CATEGORY_OPTIONS.map((category) => (
            <option key={category} value={category}>
              {titleCase(category)}
            </option>
          ))}
        </select>
        <select
          className="w-full rounded-2xl border border-borderSoft bg-panelAlt/80 px-4 py-3 text-sm text-text outline-none transition-all duration-300 ease-smooth focus:border-accent/60 focus:shadow-[0_0_0_4px_rgba(0,255,163,0.14)] sm:col-span-1"
          value={createForm.riskLevel}
          onChange={(event) => {
            const value = event.currentTarget.value as RiskLevel;
            setCreateForm((prev) => ({ ...prev, riskLevel: value }));
          }}
        >
          <option value="conservative">Conservative</option>
          <option value="moderate">Moderate</option>
          <option value="aggressive">Aggressive</option>
        </select>
        <div className="sm:col-span-6">
          <label className="mb-2 inline-flex items-center gap-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={createForm.smartAdjust}
              onChange={(event) => {
                const checked = event.currentTarget.checked;
                setCreateForm((prev) => ({ ...prev, smartAdjust: checked }));
              }}
            />
            Enable smart auto-adjust suggestion for infeasible goals
          </label>
        </div>
        <div className="sm:col-span-6">
          <Button type="submit" isLoading={isCreating}>
            Add Goal
          </Button>
        </div>
      </form>

      {lastPlanSummary ? (
        <div className="mt-3 rounded-2xl border border-white/10 bg-panelAlt/65 p-3 text-sm text-muted">
          <p className="font-medium text-text">Last goal planning result</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <p>
              Original SIP: <span className="text-text">{currency(lastPlanSummary.raw_sip)}</span>
            </p>
            <p>
              Final SIP: <span className="text-text">{currency(lastPlanSummary.final_sip)}</span>
            </p>
            <p>
              Original target date: <span className="text-text">{lastPlanSummary.original_target_date}</span>
            </p>
            <p>
              Adjusted target date: <span className="text-text">{lastPlanSummary.adjusted_target_date}</span>
            </p>
          </div>
          <p className="mt-2 text-text">
            {lastPlanSummary.adjusted
              ? `This goal was adjusted to ${currency(lastPlanSummary.final_sip)}/month to match your financial capacity.`
              : `This SIP is within your safe investment limit at ${currency(lastPlanSummary.final_sip)}/month.`}
          </p>
          <p className="mt-1 text-text">
            Expected Return Assumed: {(lastPlanSummary.expected_return * 100).toFixed(0)}% annually (based on your risk profile)
          </p>
          <p className="mt-1">Monthly return assumption: {(lastPlanSummary.monthly_return * 100).toFixed(2)}%</p>
          <p className="mt-1">{lastPlanSummary.return_assumption_note}</p>
          <p className="mt-1">Constraint reason: {lastPlanSummary.reason}</p>
          {lastPlanSummary.timeline_adjusted ? (
            <p className="mt-1 text-text">To keep your SIP within safe limits, your goal timeline has been extended.</p>
          ) : null}
          <p className="mt-1">
            Timeline: {lastPlanSummary.original_timeline.toFixed(2)}y -> {lastPlanSummary.adjusted_timeline.toFixed(2)}y
          </p>
          <p className="mt-1">Options: {lastPlanSummary.adjustment_options.join(" | ")}</p>
          <p className="mt-1">Reason: {lastPlanSummary.ai_reasoning}</p>
        </div>
      ) : null}

      <div className="mt-5 space-y-3">
        {isLoading ? <p className="text-sm text-muted">Loading goals...</p> : null}

        {!isLoading && goals.length === 0 ? (
          <p className="text-sm text-muted">No goals found for this status.</p>
        ) : null}

        {goals.map((goal) => {
          const isEditing = editingGoalId === goal.id;
          const isBusy = busyGoalId === goal.id;

          return (
            <div
              key={goal.id}
              className="neon-outline rounded-2xl border border-white/10 bg-panelAlt/75 p-4 transition-all duration-300 ease-smooth"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-text">{goal.title}</p>
                  <p className="text-xs text-muted">Target: {currency(goal.target_amount)}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-white/15 bg-black/20 px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted">
                    {goal.status}
                  </span>
                  <span className="rounded-full border border-accent/25 bg-accent/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-accent">
                    {goal.category}
                  </span>
                </div>
              </div>

              {!isEditing ? (
                <>
                  <div className="mt-3 grid gap-1 text-sm text-muted sm:grid-cols-3">
                      <p>
                        SIP: <span className="text-accent">{currency(goal.monthly_sip_required)}</span>
                      </p>
                      <p>
                        Target date: <span className="text-text">{goal.target_date.slice(0, 10)}</span>
                      </p>
                      <p>
                        Expected return: <span className="text-text">{Math.round(goal.expected_annual_return * 100)}%</span>
                      </p>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button type="button" className="bg-panelAlt text-text" disabled={isBusy} onClick={() => startEdit(goal)}>
                      Edit
                    </Button>

                    {goal.status === "active" ? (
                      <Button
                        type="button"
                        className="bg-panelAlt text-text"
                        disabled={isBusy}
                        onClick={() => updateGoalStatus(goal.id, "paused")}
                      >
                        Pause
                      </Button>
                    ) : null}

                    {goal.status === "paused" ? (
                      <Button
                        type="button"
                        className="bg-panelAlt text-text"
                        disabled={isBusy}
                        onClick={() => updateGoalStatus(goal.id, "active")}
                      >
                        Resume
                      </Button>
                    ) : null}

                    {(goal.status === "active" || goal.status === "paused") ? (
                      <Button
                        type="button"
                        className="bg-panelAlt text-text"
                        disabled={isBusy}
                        onClick={() => updateGoalStatus(goal.id, "completed")}
                      >
                        Mark Complete
                      </Button>
                    ) : null}

                    <Button
                      type="button"
                      className="bg-danger text-white"
                      disabled={isBusy}
                      onClick={() => deleteWithConfirm(goal.id, goal.title)}
                    >
                      Delete
                    </Button>
                  </div>
                </>
              ) : (
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <Input
                    value={editForm.title}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      setEditForm((prev) => ({ ...prev, title: value }));
                    }}
                  />
                  <Input
                    type="number"
                    min={1}
                    value={editForm.targetAmount}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      setEditForm((prev) => ({ ...prev, targetAmount: value }));
                    }}
                  />
                  <Input
                    type="date"
                    value={editForm.targetDate}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      setEditForm((prev) => ({ ...prev, targetDate: value }));
                    }}
                  />
                  <select
                    className="w-full rounded-2xl border border-borderSoft bg-panelAlt/80 px-4 py-3 text-sm text-text outline-none transition-all duration-300 ease-smooth focus:border-accent/60 focus:shadow-[0_0_0_4px_rgba(0,255,163,0.14)]"
                    value={editForm.riskLevel}
                    onChange={(event) => {
                      const value = event.currentTarget.value as RiskLevel;
                      setEditForm((prev) => ({ ...prev, riskLevel: value }));
                    }}
                  >
                    <option value="conservative">Conservative</option>
                    <option value="moderate">Moderate</option>
                    <option value="aggressive">Aggressive</option>
                  </select>
                  <Input
                    type="number"
                    min={0}
                    placeholder="Monthly SIP override (optional)"
                    value={editForm.monthlySipOverride}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      setEditForm((prev) => ({ ...prev, monthlySipOverride: value }));
                    }}
                    className="sm:col-span-2"
                  />
                  <div className="sm:col-span-2 flex flex-wrap gap-2">
                    <Button type="button" isLoading={isBusy} onClick={() => onSaveEdit(goal.id)}>
                      Save
                    </Button>
                    <Button
                      type="button"
                      className="bg-panelAlt text-text"
                      disabled={isBusy}
                      onClick={() => setEditingGoalId(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {feasibilityError ? (
        <FeasibilityModal
          payload={feasibilityError}
          onClose={() => setFeasibilityError(null)}
          onApplyAutoAdjust={handleApplyAutoAdjust}
          applyingAutoAdjust={applyingAutoAdjust}
        />
      ) : null}
    </Card>
  );
}
