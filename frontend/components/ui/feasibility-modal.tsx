import { Button } from "@/components/ui/button";
import { currency } from "@/lib/utils";
import type { GoalFeasibilityError } from "@/services/goalService";

interface FeasibilityModalProps {
  payload: GoalFeasibilityError;
  onClose: () => void;
  onApplyAutoAdjust: () => Promise<void>;
  applyingAutoAdjust: boolean;
}

export function FeasibilityModal({
  payload,
  onClose,
  onApplyAutoAdjust,
  applyingAutoAdjust,
}: FeasibilityModalProps) {
  const shortfall = payload.shortfall_amount ?? Math.max(payload.required_sip - payload.suggested_sip, 0);
  const availableSurplus = payload.available_surplus ?? payload.available_savings;
  const safetyBuffer = payload.safety_buffer_amount ?? 0;
  const investableSurplus = payload.investable_surplus ?? payload.suggested_sip;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-white/10 bg-panel p-5 shadow-card">
        <h4 className="text-xl font-semibold text-text">This goal is not financially feasible</h4>
        <p className="mt-1 text-sm text-muted">{payload.reason}</p>

        <div className="mt-4 grid gap-2 rounded-2xl border border-white/10 bg-panelAlt/60 p-3 sm:grid-cols-3">
          <div>
            <p className="text-xs text-muted">Required SIP</p>
            <p className="text-sm font-semibold text-text">{currency(payload.required_sip)}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Investable Surplus</p>
            <p className="text-sm font-semibold text-text">{currency(investableSurplus)}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Suggested SIP</p>
            <p className="text-sm font-semibold text-text">{currency(payload.suggested_sip)}</p>
          </div>
        </div>

        <div className="mt-3 grid gap-2 rounded-2xl border border-white/10 bg-panelAlt/60 p-3 sm:grid-cols-3">
          <div>
            <p className="text-xs text-muted">Available Surplus</p>
            <p className="text-sm font-semibold text-text">{currency(availableSurplus)}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Safety Buffer</p>
            <p className="text-sm font-semibold text-text">{currency(safetyBuffer)}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Shortfall</p>
            <p className="text-sm font-semibold text-text">{currency(shortfall)}</p>
          </div>
        </div>

        <div className="mt-3 rounded-2xl border border-white/10 bg-panelAlt/60 p-3">
          <p className="text-sm font-medium text-text">Suggestions</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
            {payload.suggestions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        {payload.auto_adjustment ? (
          <div className="mt-3 rounded-2xl border border-accent/20 bg-accent/10 p-3 text-sm text-text">
            <p className="font-medium">Smart adjust recommendation</p>
            <p className="mt-1 text-muted">
              Extend timeline to {payload.auto_adjustment.adjusted_years} years (target date {payload.auto_adjustment.adjusted_target_date})
              so your SIP aligns near {currency(payload.auto_adjustment.feasible_sip)} per month.
            </p>
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          {payload.auto_adjustment ? (
            <Button type="button" isLoading={applyingAutoAdjust} onClick={() => void onApplyAutoAdjust()}>
              Adjust Goal Automatically
            </Button>
          ) : null}
          <Button type="button" className="border border-white/10 bg-panelAlt text-text shadow-none" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
