import { ArrowRight, Gauge, PlaneTakeoff, Ticket, TrendingUp, UsersRound } from "lucide-react";
import { useMemo } from "react";
import { useLocation } from "wouter";
import {
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis
} from "recharts";
import { ActionBadge, ConfidenceBadge } from "../components/ActionBadge";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import type { OverviewArtifact, RouteMarket } from "../data/types";
import { formatCompact, formatCurrency, formatPercent } from "../lib/format";

const actionColors: Record<string, string> = {
  "Evaluate yield": "#087f8c",
  "Protect share": "#d35d42",
  "Review capacity": "#d18a12",
  "Review fare position": "#7657c8",
  "Hold and monitor": "#6b7785"
};

function OpportunityTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: RouteMarket }> }) {
  if (!active || !payload?.[0]) return null;
  const route = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{route.origin} to {route.destination} | {route.carrier}</strong>
      <span>Fare index: {route.fareIndex.toFixed(2)}x</span>
      <span>Load factor: {formatPercent(route.loadFactor)}</span>
      <span>Forecast YoY: {formatPercent(route.forecast.yearOverYearChange)}</span>
      <span>{route.action}</span>
    </div>
  );
}

export function OverviewPage({ artifact }: { artifact: OverviewArtifact }) {
  const [, navigate] = useLocation();
  const metrics = useMemo(() => {
    const totalPassengers = artifact.routes.reduce((sum, route) => sum + route.passengers, 0);
    const totalSeats = artifact.routes.reduce((sum, route) => sum + route.seats, 0);
    const weightedFare = artifact.routes.reduce((sum, route) => sum + route.baselineFare * route.passengers, 0) / totalPassengers;
    const revenueProxy = artifact.routes.reduce((sum, route) => sum + route.baselineFare * route.passengers, 0);
    return { totalPassengers, loadFactor: totalPassengers / totalSeats, weightedFare, revenueProxy };
  }, [artifact.routes]);

  const sortedRoutes = [...artifact.routes].sort((a, b) => b.score - a.score);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Observed DOT route pricing workspace"
        title="Turn market evidence into review-ready actions."
        description="Prioritize a route, inspect fare and capacity evidence, and test an assumption-based scenario without overstating causality."
        actions={<button className="primary-button" onClick={() => navigate("/scenario")}><PlaneTakeoff size={17} />Open scenario lab</button>}
      />

      <section className="kpi-grid" aria-label="Portfolio summary">
        <KpiCard label="Weighted fare" value={formatCurrency(metrics.weightedFare)} detail="Passenger-weighted across visible markets" icon={Ticket} />
        <KpiCard label="Passenger volume" value={formatCompact(metrics.totalPassengers)} detail="Latest route periods in scope" icon={UsersRound} />
        <KpiCard label="Network load factor" value={formatPercent(metrics.loadFactor)} detail="Passengers divided by available seats" icon={Gauge} />
        <KpiCard label="Revenue proxy" value={formatCurrency(metrics.revenueProxy / 1_000_000, 1) + "M"} detail="Fare multiplied by passenger volume" icon={PlaneTakeoff} />
        <KpiCard label="Forecast WAPE" value={formatPercent(artifact.forecastModel.wape)} detail={`${formatCompact(artifact.forecastModel.validationObservations)} held-out observations`} icon={TrendingUp} tone="positive" />
      </section>

      <Panel
        title="Route opportunity queue"
        subtitle="Ranked by transparent fare, share, utilization, and conditional forecast rules"
        actions={<span className="data-chip">2025 Q2 observed</span>}
      >
        <div className="table-scroll">
          <table className="decision-table">
            <thead><tr><th>Market</th><th>Recommended review</th><th>Core signal</th><th>Confidence</th><th>Score</th><th><span className="sr-only">Open</span></th></tr></thead>
            <tbody>
              {sortedRoutes.slice(0, 18).map((route) => (
                <tr key={route.id}>
                  <td><strong>{route.origin} to {route.destination}</strong><span>{route.carrierName}</span></td>
                  <td><ActionBadge action={route.action} /></td>
                  <td className="rationale-cell">{route.rationale}</td>
                  <td><ConfidenceBadge confidence={route.confidence} /></td>
                  <td><strong>{route.score}</strong><span>/ 100</span></td>
                  <td><button className="icon-button" aria-label={`Open ${route.origin} to ${route.destination} scenario`} onClick={() => navigate(`/scenario?market=${route.id}`)}><ArrowRight size={18} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="two-column-grid">
        <Panel title="Pricing posture map" subtitle="Fare position versus current load factor. Bubble size represents passenger volume.">
          <div className="chart-area" role="img" aria-label="Scatter chart of fare index and load factor by route">
            <div className="chart-visual" aria-hidden="true">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 15, bottom: 15, left: 0 }}>
                  <CartesianGrid stroke="#e7edf1" vertical={false} />
                  <XAxis type="number" dataKey="fareIndex" domain={["auto", "auto"]} tick={{ fill: "#566773", fontSize: 12 }} label={{ value: "Fare index vs competitors", position: "insideBottom", offset: -8, fill: "#566773", fontSize: 12 }} />
                  <YAxis type="number" dataKey="loadFactor" domain={[0.75, 0.96]} tickFormatter={(value) => `${Math.round(value * 100)}%`} tick={{ fill: "#566773", fontSize: 12 }} width={46} />
                  <ZAxis type="number" dataKey="passengers" range={[80, 340]} />
                  <Tooltip content={<OpportunityTooltip />} cursor={{ strokeDasharray: "4 4" }} />
                  <Scatter data={artifact.routes}>
                    {artifact.routes.map((route) => <Cell key={route.id} fill={actionColors[route.action]} fillOpacity={0.82} />)}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="chart-legend" aria-label="Action legend">
            {Object.entries(actionColors).map(([label, color]) => <span key={label}><i style={{ background: color }} />{label}</span>)}
          </div>
        </Panel>

        <Panel title="How to read the queue" subtitle="A transparent triage rule, not an automated fare setter">
          <ol className="workflow-list">
            <li><span>01</span><div><strong>Signal</strong><p>Fare position, load factor, share, concentration, and observed movement identify the review question.</p></div></li>
            <li><span>02</span><div><strong>Forecast</strong><p>A time-validated model estimates next-quarter passengers conditional on unchanged commercial inputs.</p></div></li>
            <li><span>03</span><div><strong>Scenario</strong><p>The analyst changes fare, capacity, competitor price, demand regime, and an explicit elasticity assumption.</p></div></li>
            <li><span>04</span><div><strong>Decision record</strong><p>Outputs distinguish observed values, calculations, model implications, and analyst assumptions.</p></div></li>
          </ol>
        </Panel>
      </div>
    </div>
  );
}
