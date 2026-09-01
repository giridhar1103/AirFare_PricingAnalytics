import { AlertTriangle, ArrowRight, CheckCircle2, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { useLocation } from "wouter";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import { RangeControl } from "../components/RangeControl";
import { AiDecisionBrief } from "../components/AiDecisionBrief";
import type { RouteMarket } from "../data/types";
import { formatCompact, formatCurrency, formatPercent, signedPercent } from "../lib/format";
import { simulateScenario, supportLabel } from "../lib/scenario";

const demandFactors = { soft: 0.95, base: 1, strong: 1.05 } as const;

export function ScenarioPage({ routes }: { routes: RouteMarket[] }) {
  const [, setLocation] = useLocation();
  const searchParams = new URLSearchParams(window.location.search);
  const initialId = searchParams.get("market");
  const initialRoute = routes.find((item) => item.id === initialId) ?? routes[0];
  const [selectedId, setSelectedId] = useState(initialRoute.id);
  const [fareChange, setFareChange] = useState(3);
  const [capacityChange, setCapacityChange] = useState(0);
  const [competitorChange, setCompetitorChange] = useState(0);
  const [elasticityAssumption, setElasticityAssumption] = useState(initialRoute.scenarioPolicy.defaultElasticity);
  const [demandRegime, setDemandRegime] = useState<keyof typeof demandFactors>("base");
  const [costEnabled, setCostEnabled] = useState(false);
  const [unitCost, setUnitCost] = useState(120);
  const route = routes.find((item) => item.id === selectedId) ?? routes[0];

  const result = useMemo(() => simulateScenario({
    baselineFare: route.baselineFare,
    baselinePassengers: route.passengers,
    baselineSeats: route.seats,
    elasticity: elasticityAssumption,
    elasticityLow: route.scenarioPolicy.sensitivityLow,
    elasticityHigh: route.scenarioPolicy.sensitivityHigh,
    fareChange: fareChange / 100,
    capacityChange: capacityChange / 100,
    demandFactor: demandFactors[demandRegime],
    competitorFareChange: competitorChange / 100,
    unitCost: costEnabled ? unitCost : undefined
  }), [route, fareChange, capacityChange, competitorChange, elasticityAssumption, demandRegime, costEnabled, unitCost]);

  const support = supportLabel(result.proposedFare, route.observedFareMin, route.observedFareMax);
  const positive = result.revenueChange > 0;
  const neutral = Math.abs(result.revenueChange) < 0.0005;
  const resultAction = support === "Extrapolation"
    ? "Outside observed fare support"
    : result.spillPassengers > 0
      ? "Capacity constraint binds"
      : neutral
        ? "No material revenue proxy change"
      : positive
        ? "Revenue proxy increases under this assumption"
        : "Revenue proxy decreases under this assumption";

  const comparisonData = [
    { name: "Passengers", baseline: 100, scenario: result.passengers / route.passengers * 100 },
    { name: "Revenue proxy", baseline: 100, scenario: result.revenue / result.baselineRevenue * 100 }
  ];

  const changeMarket = (id: string) => {
    setSelectedId(id);
    const nextRoute = routes.find((item) => item.id === id);
    if (nextRoute) setElasticityAssumption(nextRoute.scenarioPolicy.defaultElasticity);
    setLocation(`/scenario?market=${encodeURIComponent(id)}`);
  };
  const reset = () => {
    setFareChange(0);
    setCapacityChange(0);
    setCompetitorChange(0);
    setElasticityAssumption(route.scenarioPolicy.defaultElasticity);
    setDemandRegime("base");
    setCostEnabled(false);
  };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Interactive decision model"
        title="Stress test a fare plan before you recommend it."
        description="Change fare, capacity, competitor pricing, demand conditions, and the assumed demand response. FareLab returns transparent scenario math, capacity constraints, and a sensitivity range."
        actions={<button className="secondary-button" onClick={reset}><RotateCcw size={16} />Reset scenario</button>}
      />

      <div className="scenario-layout">
        <aside className="scenario-controls" aria-label="Scenario inputs">
          <div className="control-header"><span>Scenario inputs</span><small>All changes versus baseline</small></div>
          <label className="select-field"><span>Route and carrier</span><select value={selectedId} onChange={(event) => changeMarket(event.target.value)}>{routes.map((item) => <option key={item.id} value={item.id}>{item.origin} to {item.destination} | {item.carrier}</option>)}</select></label>
          <RangeControl id="fare-change" label="Your fare change" value={fareChange} min={-15} max={15} step={1} suffix="%" helper="Fare" onChange={setFareChange} />
          <RangeControl id="capacity-change" label="Capacity change" value={capacityChange} min={-20} max={20} step={1} suffix="%" helper="Seats" onChange={setCapacityChange} />
          <RangeControl id="competitor-change" label="Competitor fare change" value={competitorChange} min={-10} max={10} step={1} suffix="%" helper="Market" onChange={setCompetitorChange} />
          <RangeControl id="elasticity-assumption" label="Assumed price elasticity" value={elasticityAssumption} min={-2} max={-0.2} step={0.1} suffix="" helper="Assumption" onChange={setElasticityAssumption} />
          <fieldset className="segmented-field"><legend>Demand regime</legend><div>{(["soft", "base", "strong"] as const).map((regime) => <button key={regime} type="button" className={demandRegime === regime ? "selected" : ""} onClick={() => setDemandRegime(regime)}>{regime[0].toUpperCase() + regime.slice(1)}</button>)}</div><small>Soft and strong apply a 5% demand shift.</small></fieldset>
          <div className="cost-assumption">
            <label className="toggle-row"><input type="checkbox" checked={costEnabled} onChange={(event) => setCostEnabled(event.target.checked)} /><span>Include analyst unit cost</span></label>
            {costEnabled && <label className="number-field"><span>Assumed unit cost</span><div><span>$</span><input type="number" min="0" max={route.baselineFare * 2} value={unitCost} onChange={(event) => setUnitCost(Number(event.target.value))} /></div><small>User-provided assumption, not observed data</small></label>}
          </div>
        </aside>

        <div className="scenario-results">
          <section className={`decision-banner ${positive ? "decision-positive" : "decision-warning"}`}>
            <div className="decision-icon">{positive ? <CheckCircle2 size={22} /> : <AlertTriangle size={22} />}</div>
            <div><span>Assumption-based result</span><h2>{resultAction}</h2><p>{route.origin} to {route.destination} | {route.carrierName} | {support}</p></div>
            <div className="decision-change"><span>Revenue proxy change</span><strong>{signedPercent(result.revenueChange)}</strong></div>
          </section>

          <section className="result-grid" aria-label="Scenario outputs">
            <article><span>Proposed fare</span><strong>{formatCurrency(result.proposedFare)}</strong><small>From {formatCurrency(route.baselineFare)}</small></article>
            <article><span>Passengers</span><strong>{formatCompact(result.passengers)}</strong><small className={result.passengerChange >= 0 ? "value-positive" : "value-negative"}>{signedPercent(result.passengerChange)}</small></article>
            <article><span>Revenue proxy</span><strong>{formatCurrency(result.revenue / 1_000_000, 2)}M</strong><small>Sensitivity: {formatCurrency(result.revenueLow / 1_000_000, 2)}M to {formatCurrency(result.revenueHigh / 1_000_000, 2)}M</small></article>
            <article><span>Load factor</span><strong>{formatPercent(result.loadFactor)}</strong><small>{result.spillPassengers > 0 ? `${formatCompact(result.spillPassengers)} potential spill` : "Within capacity"}</small></article>
            {costEnabled && <article><span>Contribution proxy</span><strong>{formatCurrency((result.contribution ?? 0) / 1_000_000, 2)}M</strong><small>Uses your {formatCurrency(unitCost)} unit cost</small></article>}
          </section>

          <div className="two-column-grid scenario-detail-grid">
            <Panel title="Baseline versus scenario" subtitle="Both measures are indexed to baseline = 100">
              <div className="scenario-chart" role="img" aria-label="Indexed comparison of baseline and scenario passengers and revenue proxy">
                <ResponsiveContainer width="100%" height="100%"><BarChart data={comparisonData} barGap={6}><CartesianGrid stroke="#e7edf1" vertical={false}/><XAxis dataKey="name" tick={{ fill: "#566773", fontSize: 12 }} tickLine={false} axisLine={false}/><YAxis tickFormatter={(value) => value.toFixed(0)} domain={["auto", "auto"]} tick={{ fill: "#566773", fontSize: 12 }} tickLine={false} axisLine={false}/><Tooltip formatter={(value: number) => `${value.toFixed(1)} index points`} contentStyle={{ border: "1px solid #dce5ea", borderRadius: 8 }}/><ReferenceLine y={100} stroke="#9aa8b4" strokeDasharray="4 4"/><Bar dataKey="baseline" name="Baseline" fill="#c4d0d9" radius={[4,4,0,0]}/><Bar dataKey="scenario" name="Scenario" radius={[4,4,0,0]}>{comparisonData.map((item) => <Cell key={item.name} fill={positive ? "#087f8c" : "#d18a12"}/>)}</Bar></BarChart></ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Why this result" subtitle="Calculation trail for analyst review">
              <dl className="calculation-list">
                <div><dt>Elasticity assumption</dt><dd>{elasticityAssumption.toFixed(2)}<span>Sensitivity {route.scenarioPolicy.sensitivityLow.toFixed(2)} to {route.scenarioPolicy.sensitivityHigh.toFixed(2)}</span></dd></div>
                <div><dt>Assumption source</dt><dd>Analyst supplied<span>Not estimated from the DOT panel</span></dd></div>
                <div><dt>Competitor response</dt><dd>0.15 cross-price term<span>Governed scenario assumption</span></dd></div>
                <div><dt>Fare support</dt><dd>{support}<span>{formatCurrency(route.observedFareMin)} to {formatCurrency(route.observedFareMax)}</span></dd></div>
                <div><dt>Demand regime</dt><dd>{demandRegime[0].toUpperCase() + demandRegime.slice(1)}<span>{signedPercent(demandFactors[demandRegime] - 1)}</span></dd></div>
                <div><dt>Revenue break-even</dt><dd>-1.00 elasticity<span>Constant-elasticity local rule</span></dd></div>
              </dl>
            </Panel>
          </div>

          <AiDecisionBrief request={{
            routeId: route.id,
            fareChange: fareChange / 100,
            capacityChange: capacityChange / 100,
            competitorFareChange: competitorChange / 100,
            elasticity: elasticityAssumption,
            demandFactor: demandFactors[demandRegime],
            unitCost: costEnabled ? unitCost : undefined
          }} />

          <div className="assumption-note"><AlertTriangle size={17}/><p><strong>Interpretation boundary:</strong> This is scenario arithmetic, not a causal forecast or automated fare recommendation. Elasticity and competitor response are analyst assumptions. Revenue proxy excludes optional-service revenue and accounting cost. Capacity changes do not model schedule feasibility.</p></div>
        </div>
      </div>
    </div>
  );
}
