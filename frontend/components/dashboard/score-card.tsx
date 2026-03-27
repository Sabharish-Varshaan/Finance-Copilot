import { Card } from "@/components/ui/card";
import type { MoneyHealthScore } from "@/types";

interface ScoreCardProps {
  score: MoneyHealthScore;
}

type Tone = {
  trackClass: string;
  fillClass: string;
  badgeClass: string;
};

function emergencyFundTone(months: number): Tone {
  if (months < 3) {
    return {
      trackClass: "bg-rose-950/45",
      fillClass: "bg-gradient-to-r from-rose-700 via-rose-500 to-rose-300 shadow-[0_0_14px_rgba(251,113,133,0.45)]",
      badgeClass: "text-rose-200",
    };
  }
  if (months <= 6) {
    return {
      trackClass: "bg-amber-950/35",
      fillClass: "bg-gradient-to-r from-amber-700 via-amber-500 to-amber-300 shadow-[0_0_14px_rgba(251,191,36,0.4)]",
      badgeClass: "text-amber-200",
    };
  }
  return {
    trackClass: "bg-emerald-950/40",
    fillClass: "bg-gradient-to-r from-emerald-700 via-emerald-500 to-emerald-300 shadow-[0_0_14px_rgba(16,185,129,0.4)]",
    badgeClass: "text-emerald-200",
  };
}

function debtRatioTone(debtRatio: number): Tone {
  if (debtRatio > 0.4) {
    return {
      trackClass: "bg-rose-950/45",
      fillClass: "bg-gradient-to-r from-rose-800 via-rose-600 to-rose-400 shadow-[0_0_14px_rgba(244,63,94,0.45)]",
      badgeClass: "text-rose-200",
    };
  }
  if (debtRatio > 0.3) {
    return {
      trackClass: "bg-orange-950/45",
      fillClass: "bg-gradient-to-r from-orange-800 via-orange-600 to-orange-300 shadow-[0_0_14px_rgba(251,146,60,0.45)]",
      badgeClass: "text-orange-200",
    };
  }
  if (debtRatio > 0.2) {
    return {
      trackClass: "bg-amber-950/35",
      fillClass: "bg-gradient-to-r from-amber-700 via-amber-500 to-amber-300 shadow-[0_0_14px_rgba(245,158,11,0.4)]",
      badgeClass: "text-amber-200",
    };
  }
  return {
    trackClass: "bg-emerald-950/40",
    fillClass: "bg-gradient-to-r from-emerald-700 via-emerald-500 to-emerald-300 shadow-[0_0_14px_rgba(16,185,129,0.4)]",
    badgeClass: "text-emerald-200",
  };
}

function savingsRateTone(savingsRate: number): Tone {
  if (savingsRate < 0.2) {
    return {
      trackClass: "bg-rose-950/45",
      fillClass: "bg-gradient-to-r from-rose-800 via-rose-600 to-rose-400 shadow-[0_0_14px_rgba(244,63,94,0.45)]",
      badgeClass: "text-rose-200",
    };
  }
  if (savingsRate <= 0.4) {
    return {
      trackClass: "bg-amber-950/35",
      fillClass: "bg-gradient-to-r from-amber-700 via-amber-500 to-amber-300 shadow-[0_0_14px_rgba(245,158,11,0.4)]",
      badgeClass: "text-amber-200",
    };
  }
  if (savingsRate <= 0.6) {
    return {
      trackClass: "bg-lime-950/40",
      fillClass: "bg-gradient-to-r from-lime-700 via-lime-500 to-lime-300 shadow-[0_0_14px_rgba(132,204,22,0.4)]",
      badgeClass: "text-lime-200",
    };
  }
  return {
    trackClass: "bg-emerald-950/40",
    fillClass: "bg-gradient-to-r from-emerald-700 via-emerald-500 to-emerald-300 shadow-[0_0_14px_rgba(16,185,129,0.4)]",
    badgeClass: "text-emerald-200",
  };
}

function investmentTone(isActive: boolean): Tone {
  if (!isActive) {
    return {
      trackClass: "bg-orange-950/45",
      fillClass: "bg-gradient-to-r from-orange-800 via-orange-600 to-orange-300 shadow-[0_0_14px_rgba(251,146,60,0.45)]",
      badgeClass: "text-orange-200",
    };
  }
  return {
    trackClass: "bg-emerald-950/40",
    fillClass: "bg-gradient-to-r from-emerald-700 via-emerald-500 to-emerald-300 shadow-[0_0_14px_rgba(16,185,129,0.4)]",
    badgeClass: "text-emerald-200",
  };
}

export function ScoreCard({ score }: ScoreCardProps) {
  const emergencyTone = emergencyFundTone(score.breakdown.emergency_fund_months);
  const debtTone = debtRatioTone(score.breakdown.debt_ratio);
  const savingsTone = savingsRateTone(score.breakdown.savings_rate);
  const investmentToneValue = investmentTone(score.breakdown.investment_presence);

  const bars = [
    {
      label: "Emergency Fund",
      value: score.breakdown.component_scores.emergency_fund,
      max: 30,
      info: `${score.breakdown.emergency_fund_months} months`,
      tone: emergencyTone,
    },
    {
      label: "Debt Ratio",
      value: score.breakdown.component_scores.debt_ratio,
      max: 25,
      info: `${(score.breakdown.debt_ratio * 100).toFixed(1)}%`,
      tone: debtTone,
    },
    {
      label: "Savings Rate",
      value: score.breakdown.component_scores.savings_rate,
      max: 30,
      info: `${(score.breakdown.savings_rate * 100).toFixed(1)}%`,
      tone: savingsTone,
    },
    {
      label: "Investment Presence",
      value: score.breakdown.component_scores.investment_presence,
      max: 15,
      info: score.breakdown.investment_presence ? "Active" : "Not active",
      tone: investmentToneValue,
    },
  ];

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute -right-24 -top-24 h-64 w-64 rounded-full bg-accent/10 blur-3xl" />
      <p className="relative text-xs uppercase tracking-[0.18em] text-muted">Money Health Score</p>
      <div className="relative mt-3 flex items-end gap-3">
        <h2 className="text-6xl font-semibold text-accent drop-shadow-[0_0_18px_rgba(0,255,163,0.32)]">{score.score}</h2>
        <p className="mb-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs text-accent">Grade {score.grade}</p>
      </div>
      <div className="relative mt-6 space-y-3">
        {bars.map((bar) => {
          const width = Math.max(8, Math.min(100, (bar.value / bar.max) * 100));

          return (
            <div key={bar.label} className="rounded-xl border border-white/5 bg-panelAlt/70 p-3">
              <div className="mb-2 flex items-center justify-between text-xs text-muted">
                <span>{bar.label}</span>
                <span className={bar.tone.badgeClass}>{bar.info}</span>
              </div>
              <div className={`h-2.5 rounded-full ${bar.tone.trackClass}`}>
                <div
                  className={`h-full rounded-full ${bar.tone.fillClass} transition-all duration-500 ease-smooth`}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="relative mt-4 rounded-xl border border-accent/20 bg-accent/5 px-3 py-2 text-xs text-muted">
        Keep your debt ratio below 30% and emergency fund above 6 months for stronger resilience.
      </div>
    </Card>
  );
}
