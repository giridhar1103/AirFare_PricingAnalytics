import { AlertTriangle, CheckCircle2, Sigma, TrendingUp } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import type { OverviewArtifact } from "../data/types";
import { formatCompact, formatPercent } from "../lib/format";

export function ModelLabPage({ artifact }: { artifact: OverviewArtifact }) {
  const [selectedId, setSelectedId] = useState(artifact.routes[0].id);
  const route = artifact.routes.find((item) => item.id === selectedId) ?? artifact.routes[0];
  const model = artifact.forecastModel;
  const audit = artifact.identificationAudit;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Forecast and identification workbench"
        title="Forecast what is predictable. Flag what is not identified."
        description="The demand forecast passes time-based validation. The fare-response models fail the economic sign check, so FareLab keeps elasticity as an explicit scenario assumption."
        actions={<label className="select-field compact-select"><span>Route and carrier</span><select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>{artifact.routes.map((item) => <option key={item.id} value={item.id}>{item.origin} to {item.destination} | {item.carrier}</option>)}</select></label>}
      />

      <div className="elasticity-hero">
        <section className="estimate-card">
          <span className="estimate-label">Held-out gradient boosting WAPE</span>
          <strong>{formatPercent(model.wape)}</strong>
          <div className="benchmark-bars" aria-label="Forecast error comparison">
            <div><span>Seasonal naive</span><i><b style={{ width: `${Math.min(model.seasonalNaiveWape / 0.2 * 100, 100)}%` }} /></i><strong>{formatPercent(model.seasonalNaiveWape)}</strong></div>
            <div><span>ML champion</span><i><b className="benchmark-champion" style={{ width: `${Math.min(model.wape / 0.2 * 100, 100)}%` }} /></i><strong>{formatPercent(model.wape)}</strong></div>
          </div>
          <div className="estimate-footer"><span className="classification classification-positive">Time-validated champion</span><span>{formatCompact(model.validationObservations)} holdout rows</span></div>
        </section>
        <section className="interpretation-card">
          <span className="section-kicker"><TrendingUp size={17} />Conditional {route.forecast.period} forecast</span>
          <h2>{route.origin} to {route.destination} | {route.carrier}: {formatCompact(route.forecast.passengers)} passengers</h2>
          <p>The calibrated {formatPercent(model.intervalLevel, 0)} interval is {formatCompact(route.forecast.low)} to {formatCompact(route.forecast.high)} passengers. The model assumes the latest fare, seats, competitor fare, and market structure continue into the forecast quarter.</p>
          <div className="model-alert alert-info"><CheckCircle2 size={18} /><span>Out-of-fold interval coverage is {formatPercent(model.intervalCoverage)} with aggregate forecast bias of {formatPercent(model.bias)}.</span></div>
        </section>
      </div>

      <Panel title="Fare-response identification audit" subtitle="Three specifications were tested and none is approved for scenario use">
        <div className="identification-banner"><AlertTriangle size={20} /><div><strong>{audit.status}</strong><p>{audit.reason}</p></div></div>
        <div className="diagnostic-grid">
          <article><span>Passenger fixed effects</span><strong>{audit.passengerFixedEffectsCoefficient.toFixed(3)}</strong><small>Expected economic sign: negative</small><b>Rejected</b></article>
          <article><span>Market-share fixed effects</span><strong>{audit.marketShareFixedEffectsCoefficient.toFixed(3)}</strong><small>Expected economic sign: negative</small><b>Rejected</b></article>
          <article><span>IV sensitivity</span><strong>{audit.ivSensitivityCoefficient.toFixed(3)}</strong><small>Strong first stage, nonnegative second stage</small><b>Research only</b></article>
        </div>
        <p className="audit-explanation">Carriers change fares and capacity in response to demand information that quarterly public data does not observe. A positive coefficient in all three specifications is evidence that a simple regression is following commercial decisions, not tracing a causal demand curve. FareLab reports that failure instead of forcing a plausible-looking elasticity.</p>
      </Panel>

      <Panel title="Conditional forecast specification" subtitle="A predictive model for planned-input scenarios, not a causal pricing model">
        <div className="equation-block" aria-label="Next-quarter passengers are predicted from passenger lags, planned fare and seats, competitor fare, market structure, season, route distance, and carrier">
          <span>Q<sub>t+1</sub></span><b>=</b><em>f</em><span>(Q<sub>t</sub>, Q<sub>t-3</sub>, Fare<sub>t+1</sub>, Seats<sub>t+1</sub>, CompFare<sub>t+1</sub>, Share<sub>t</sub>, HHI, Season, Distance, Carrier)</span>
        </div>
        <div className="term-grid forecast-term-grid">
          <div><strong>Demand lags</strong><span>One-quarter and seasonal passenger history</span></div>
          <div><strong>Planned inputs</strong><span>Fare, seats, and competitor-fare assumptions</span></div>
          <div><strong>Market state</strong><span>Prior share, HHI, distance, and carrier</span></div>
          <div><strong>Validation</strong><span>Expanding windows for 2023, 2024, and 2025 H1</span></div>
        </div>
      </Panel>

      <div className="three-column-grid">
        <Panel title="Prediction strength" subtitle="What the model demonstrates"><ul className="check-list"><li>5.1% aggregate WAPE</li><li>1.8% aggregate bias</li><li>80.0% calibrated interval coverage</li><li>Large improvement over seasonal naive</li></ul></Panel>
        <Panel title="Known limits" subtitle="What remains unobserved"><ul className="limit-list"><li>Booking-class inventory</li><li>Search and shopping demand</li><li>Schedule quality changes</li><li>Route cost and ancillary revenue</li></ul></Panel>
        <Panel title="Decision policy" subtitle="How model outputs are used"><ul className="check-list"><li>Forecast demand conditional on inputs</li><li>Show uncertainty on every route</li><li>Keep elasticity user supplied</li><li>Never label association as causation</li></ul></Panel>
      </div>
    </div>
  );
}
