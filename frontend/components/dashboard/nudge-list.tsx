import { Card } from "@/components/ui/card";

interface NudgeListProps {
  nudges: string[];
}

export function NudgeList({ nudges }: NudgeListProps) {
  return (
    <Card>
      <h3 className="text-xl font-semibold">Smart Nudges</h3>
      <p className="mt-1 text-sm text-muted">Quick actions to improve your score.</p>
      <ul className="mt-5 space-y-3 text-sm text-muted">
        {nudges.map((nudge, index) => (
          <li
            key={nudge}
            className="rounded-2xl border border-white/10 bg-panelAlt/80 p-3 transition-all duration-300 ease-smooth hover:border-accent/30"
            style={{ animationDelay: `${index * 70}ms` }}
          >
            {nudge}
          </li>
        ))}
      </ul>
    </Card>
  );
}
