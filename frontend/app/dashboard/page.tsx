"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";

import { GoalList } from "@/components/dashboard/goal-list";
import { NudgeList } from "@/components/dashboard/nudge-list";
import { ScoreCard } from "@/components/dashboard/score-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/useAuth";
import {
  createGoal,
  deleteGoal,
  listGoals,
  type GoalCreatePayload,
  type GoalCreateResponse,
  type GoalStatusFilter,
  type GoalUpdatePayload,
  updateGoal,
} from "@/services/goalService";
import { getNudges, getScore } from "@/services/scoreService";
import type { Goal, MoneyHealthScore } from "@/types";

export default function DashboardPage() {
  const logout = useAuth((state) => state.logout);

  const [score, setScore] = useState<MoneyHealthScore | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [nudges, setNudges] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [goalsLoading, setGoalsLoading] = useState(false);
  const [selectedGoalStatus, setSelectedGoalStatus] = useState<GoalStatusFilter>("active");

  async function loadGoalsByStatus(status: GoalStatusFilter) {
    setGoalsLoading(true);
    try {
      const goalsData = await listGoals(status);
      setGoals(goalsData);
    } finally {
      setGoalsLoading(false);
    }
  }

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [scoreData, goalsData, nudgesData] = await Promise.all([
          getScore(),
          listGoals(selectedGoalStatus),
          getNudges(),
        ]);
        setScore(scoreData);
        setGoals(goalsData);
        setNudges(nudgesData.nudges);
      } catch {
        toast.error("Could not load dashboard. Complete onboarding first.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  async function handleGoalStatusChange(status: GoalStatusFilter) {
    setSelectedGoalStatus(status);
    await loadGoalsByStatus(status);
  }

  async function handleCreateGoal(payload: GoalCreatePayload): Promise<GoalCreateResponse> {
    const result = await createGoal(payload);
    await loadGoalsByStatus(selectedGoalStatus);
    return result;
  }

  async function handleUpdateGoal(goalId: number, payload: GoalUpdatePayload) {
    try {
      await updateGoal(goalId, payload);
      await loadGoalsByStatus(selectedGoalStatus);
      toast.success("Goal updated");
    } catch {
      toast.error("Could not update goal");
      throw new Error("goal-update-failed");
    }
  }

  async function handleDeleteGoal(goalId: number) {
    try {
      await deleteGoal(goalId);
      await loadGoalsByStatus(selectedGoalStatus);
      toast.success("Goal deleted");
    } catch {
      toast.error("Could not delete goal");
      throw new Error("goal-delete-failed");
    }
  }

  if (loading) {
    return (
      <main className="page-enter mx-auto w-full max-w-6xl px-4 py-10">
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
          <Skeleton className="h-80 md:col-span-2" />
        </div>
      </main>
    );
  }

  return (
    <main className="page-enter mx-auto w-full max-w-6xl px-4 py-10">
      <header className="mb-7 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight">Your Money Command Center</h1>
          <p className="text-sm text-muted">Track score, goals, and next best actions with live signals.</p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/onboarding">
            <Button className="border border-white/10 bg-panelAlt text-text shadow-none">Update Profile</Button>
          </Link>
          <Link href="/fire-planner">
            <Button className="border border-white/10 bg-panelAlt text-text shadow-none">FIRE Planner</Button>
          </Link>
          <Link href="/chat">
            <Button>Open Mentor Chat</Button>
          </Link>
          <Button
            className="bg-danger text-white"
            onClick={() => {
              logout();
              window.location.href = "/login";
            }}
          >
            Logout
          </Button>
        </div>
      </header>

      {!score ? (
        <Card>
          <p className="text-muted">No profile found.</p>
          <Link className="mt-3 inline-block text-accent" href="/onboarding">
            Complete onboarding
          </Link>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ScoreCard score={score} />
          </div>
          <NudgeList nudges={nudges} />
          <div className="lg:col-span-3">
            <GoalList
              goals={goals}
              selectedStatus={selectedGoalStatus}
              isLoading={goalsLoading}
              onStatusChange={handleGoalStatusChange}
              onCreateGoal={handleCreateGoal}
              onUpdateGoal={handleUpdateGoal}
              onDeleteGoal={handleDeleteGoal}
            />
          </div>
        </div>
      )}
    </main>
  );
}
