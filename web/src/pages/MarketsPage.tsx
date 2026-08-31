import { useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { ActionBadge, ConfidenceBadge } from "../components/ActionBadge";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import type { RouteMarket } from "../data/types";
import { formatCompact, formatCurrency, formatPercent } from "../lib/format";

export function MarketsPage({ routes }: { routes: RouteMarket[] }) {
  const [selectedId, setSelectedId] = useState(routes[0].id);
  const route = routes.find((item) => item.id === selectedId) ?? routes[0];
  const competitorFare = route.baselineFare / route.fareIndex;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Market investigation"
        title="Read the route before changing the fare."
        description="Connect fare movement with passenger volume, capacity, market position, and the conditional next-quarter forecast."
        actions={
          <label className="select-field compact-select"><span>Route and carrier</span><select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>{routes.map((item) => <option key={item.id} value={item.id}>{item.origin} to {item.destination} | {item.carrier}</option>)}</select></label>
        }
      />

      <section className="market-identity">
        <div className="route-code"><span>{route.origin}</span><i /><span>{route.destination}</span></div>
        <div className="route-description"><strong>Directional airport market</strong><span>{route.carrierName} | {route.distanceMiles.toLocaleString("en-US")} miles</span></div>
        <div className="route-decision"><ActionBadge action={route.action} /><ConfidenceBadge confidence={route.confidence} /></div>
      </section>

      <section className="metric-strip" aria-label="Selected market metrics">
        <div><span>Observed fare</span><strong>{formatCurrency(route.baselineFare)}</strong><small>Competitor average {formatCurrency(competitorFare)}</small></div>
        <div><span>Passenger volume</span><strong>{formatCompact(route.passengers)}</strong><small>Latest visible quarter</small></div>
        <div><span>Available seats</span><strong>{formatCompact(route.seats)}</strong><small>Capacity denominator</small></div>
        <div><span>Load factor</span><strong>{formatPercent(route.loadFactor)}</strong><small>Operational utilization</small></div>
        <div><span>Carrier share</span><strong>{formatPercent(route.marketShare)}</strong><small>{route.changes.shareYoYPoints >= 0 ? "+" : ""}{(route.changes.shareYoYPoints * 100).toFixed(1)} points YoY</small></div>
        <div><span>Market HHI</span><strong>{Math.round(route.hhi * 10000).toLocaleString("en-US")}</strong><small>0 to 10,000 convention</small></div>
      </section>

      <Panel title="Fare, market fare, and passenger history" subtitle="Linked quarterly series for the selected route-carrier market">
        <div className="large-chart" role="img" aria-label={`Fare and passengers over time for ${route.origin} to ${route.destination}`}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={route.history} margin={{ top: 12, right: 12, bottom: 4, left: 0 }}>
              <defs>
                <linearGradient id="passengerFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5a8dee" stopOpacity="0.24"/><stop offset="100%" stopColor="#5a8dee" stopOpacity="0.02"/></linearGradient>
              </defs>
              <CartesianGrid stroke="#e7edf1" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "#566773", fontSize: 12 }} tickLine={false} axisLine={false} />
              <YAxis yAxisId="fare" tickFormatter={(value) => `$${value}`} tick={{ fill: "#566773", fontSize: 12 }} tickLine={false} axisLine={false} width={48} />
              <YAxis yAxisId="passengers" orientation="right" tickFormatter={formatCompact} tick={{ fill: "#566773", fontSize: 12 }} tickLine={false} axisLine={false} width={54} />
              <Tooltip contentStyle={{ border: "1px solid #dce5ea", borderRadius: 8, boxShadow: "0 10px 30px rgba(20,35,50,.1)" }} formatter={(value: number, name: string) => name === "Passengers" ? formatCompact(value) : formatCurrency(value)} />
              <Legend verticalAlign="top" align="right" height={34} iconType="circle" />
              <Area yAxisId="passengers" dataKey="passengers" name="Passengers" stroke="#5a8dee" fill="url(#passengerFill)" strokeWidth={2} />
              <Line yAxisId="fare" dataKey="fare" name="Carrier fare" stroke="#102a43" strokeWidth={2.5} dot={{ r: 3, fill: "#102a43" }} />
              <Line yAxisId="fare" dataKey="competitorFare" name="Competing fare" stroke="#d18a12" strokeWidth={2} strokeDasharray="5 4" dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div className="two-column-grid market-bottom-grid">
        <Panel title="Decision evidence" subtitle="Signals contributing to the current route action">
          <div className="evidence-callout"><span>Current interpretation</span><strong>{route.rationale}</strong></div>
          <ul className="evidence-list">{route.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
        </Panel>
        <Panel title="Forecast and support" subtitle="Guardrails applied before this market enters the queue">
          <dl className="support-list">
            <div><dt>Route-carrier periods</dt><dd>{route.observations}</dd></div>
            <div><dt>Observed fare range</dt><dd>{formatCurrency(route.observedFareMin)} to {formatCurrency(route.observedFareMax)}</dd></div>
            <div><dt>{route.forecast.period} passengers</dt><dd>{formatCompact(route.forecast.passengers)}<span>{formatCompact(route.forecast.low)} to {formatCompact(route.forecast.high)}</span></dd></div>
            <div><dt>Forecast YoY</dt><dd>{route.forecast.yearOverYearChange >= 0 ? "+" : ""}{formatPercent(route.forecast.yearOverYearChange)}</dd></div>
            <div><dt>Fare index</dt><dd>{route.fareIndex.toFixed(2)}x</dd></div>
          </dl>
          <p className="formula-note">{route.forecast.assumption}.</p>
        </Panel>
      </div>
    </div>
  );
}
