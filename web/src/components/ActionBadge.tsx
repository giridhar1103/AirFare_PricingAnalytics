import type { ActionKind, Confidence } from "../data/types";

export function ActionBadge({ action }: { action: ActionKind }) {
  const className = action.toLowerCase().replace(/ /g, "-");
  return <span className={`action-badge action-${className}`}>{action}</span>;
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return <span className={`confidence-badge confidence-${confidence.toLowerCase()}`}>{confidence}</span>;
}
