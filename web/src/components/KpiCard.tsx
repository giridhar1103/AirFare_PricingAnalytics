import type { LucideIcon } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: "default" | "positive" | "warning";
}

export function KpiCard({ label, value, detail, icon: Icon, tone = "default" }: KpiCardProps) {
  return (
    <article className={`kpi-card kpi-${tone}`}>
      <div className="kpi-topline">
        <span>{label}</span>
        <Icon size={17} aria-hidden="true" />
      </div>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}
