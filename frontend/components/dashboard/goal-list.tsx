import { Card } from "@/components/ui/card";
import { currency } from "@/lib/utils";
import type { Goal } from "@/types";

interface GoalListProps {
  goals: Goal[];
}

export function GoalList({ goals }: GoalListProps) {
  return (
    <Card>
      <h3 className="text-xl font-semibold">Goals</h3>
      <p className="mt-1 text-sm text-muted">Track monthly SIP requirements and progress.</p>

      <div className="mt-5 space-y-3">
        {goals.length === 0 ? (
          <p className="text-sm text-muted">No goals found yet. Add one from your next iteration.</p>
        ) : (
          goals.map((goal) => (
            <div
              key={goal.id}
              className="neon-outline rounded-2xl border border-white/10 bg-panelAlt/75 p-4 transition-all duration-300 ease-smooth hover:-translate-y-0.5"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-text">{goal.title}</p>
                <span className="rounded-full border border-accent/25 bg-accent/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-accent">
                  {goal.category}
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span className="text-muted">Monthly SIP</span>
                <span className="font-semibold text-accent">{currency(goal.monthly_sip_required)}</span>
              </div>
              <div className="mt-1 flex items-center justify-between text-xs text-muted">
                <span>Target</span>
                <span>{currency(goal.target_amount)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
