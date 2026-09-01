import { Database, GitBranch, ShieldCheck, Sparkles, TrendingUp } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { Panel } from "../components/Panel";
import type { OverviewArtifact } from "../data/types";
import { formatCompact, formatPercent } from "../lib/format";

export function MethodologyPage({ artifact }: { artifact: OverviewArtifact }) {
  const model = artifact.forecastModel;
  const audit = artifact.identificationAudit;
  return (
    <div className="page-stack methodology-page">
      <PageHeader
        eyebrow="Methods and governance"
        title="Every recommendation should survive a review."
        description="FareLab separates observed data, calculated measures, model implications, and analyst assumptions so the decision trail stays clear."
      />

      <section className="method-cards">
        <article><Database size={20}/><span>Observed</span><strong>DOT fare, traffic, and capacity</strong><p>DB1B supplies historical sampled fares. T-100 supplies reported passengers and seats.</p></article>
        <article><GitBranch size={20}/><span>Calculated</span><strong>Market and revenue measures</strong><p>Weighted fare, load factor, share, HHI, fare index, and revenue proxy are reproducible transformations.</p></article>
        <article><TrendingUp size={20}/><span>Predicted</span><strong>Conditional passenger forecast</strong><p>A time-validated model predicts next-quarter passengers when planned fare, seats, and competitor fare are supplied.</p></article>
        <article><ShieldCheck size={20}/><span>Assumed</span><strong>Inputs owned by the analyst</strong><p>Elasticity, unit cost, and scenario changes remain clearly marked and never enter observed history.</p></article>
      </section>

      <Panel title="Data lineage" subtitle="Separate survey regimes prevent a hidden break in the historical model">
        <div className="lineage-flow">
          <div><span>Historical fares</span><strong>DB1B</strong><small>Quarterly 10% sample through 2025Q2</small></div><i>+</i>
          <div><span>Traffic and capacity</span><strong>T-100</strong><small>Monthly operating passengers and seats</small></div><i>to</i>
          <div className="lineage-primary"><span>Model mart</span><strong>Route x carrier x quarter</strong><small>Governed keys, quality gates, and lineage</small></div>
        </div>
        <div className="lineage-separate"><span>Separate monitoring layer</span><strong>DB1C monthly 40% sample from July 2025</strong><p>DB1C is not appended directly to the historical DB1B panel. It receives a separate quality history and transition analysis.</p></div>
      </Panel>

      <div className="two-column-grid">
        <Panel title="Scenario equations" subtitle="Constant-elasticity arithmetic with an explicit seat constraint">
          <div className="formula-stack">
            <code>P1 = P0 x (1 + fare change)</code>
            <code>Q demand = Q0 x (P1 / P0) ^ elasticity x (CompP1 / CompP0) ^ cross elasticity</code>
            <code>Q1 = min(Q demand x regime factor, Seats1)</code>
            <code>Revenue proxy = P1 x Q1</code>
            <code>Load factor = Q1 / Seats1</code>
          </div>
          <p className="formula-note">Elasticity is analyst controlled. Competitor response uses a governed cross-price assumption of 0.15. The displayed range evaluates the elasticity sensitivity endpoints and is not a statistical confidence interval.</p>
        </Panel>
        <Panel title="Forecast evaluation" subtitle="The ML model must beat a transparent baseline out of time">
          <dl className="metric-definitions">
            <div><dt>MAE</dt><dd>Average absolute passenger error</dd></div>
            <div><dt>WAPE</dt><dd>Total absolute error divided by total actual demand</dd></div>
            <div><dt>Bias</dt><dd>Signed aggregate over-forecast or under-forecast</dd></div>
            <div><dt>Coverage</dt><dd>Share of actuals inside the prediction interval</dd></div>
          </dl>
          <p className="formula-note">Expanding time windows prevent the model from training on future periods. Interval width is calibrated on {formatCompact(model.intervalCalibrationObservations)} observations from the 2023 and 2024 folds, then checked on {formatCompact(model.intervalEvaluationObservations)} observations from {model.intervalEvaluationPeriods.join(" and ")}. The champion WAPE is {formatPercent(model.wape)}, compared with {formatPercent(model.seasonalNaiveWape)} for the seasonal naive baseline across {formatCompact(model.validationObservations)} held-out rows. ML is a conditional demand forecast, not an automatic fare setter.</p>
        </Panel>
      </div>

      <Panel title="Identification decision" subtitle="A failed economic sign check is reported as a finding, not hidden as a tuning problem">
        <div className="identification-banner"><ShieldCheck size={20}/><div><strong>{audit.status}</strong><p>{audit.reason}</p></div></div>
        <div className="diagnostic-grid">
          <article><span>Passenger fixed effects</span><strong>{audit.passengerFixedEffectsCoefficient.toFixed(3)}</strong><small>Expected sign: negative</small><b>Rejected</b></article>
          <article><span>Market-share fixed effects</span><strong>{audit.marketShareFixedEffectsCoefficient.toFixed(3)}</strong><small>Expected sign: negative</small><b>Rejected</b></article>
          <article><span>IV sensitivity</span><strong>{audit.ivSensitivityCoefficient.toFixed(3)}</strong><small>Nonnegative second stage</small><b>Research only</b></article>
        </div>
        <p className="audit-explanation">Quarterly public data does not observe the private demand signals airlines use when changing fares and capacity. FareLab therefore does not use any of these coefficients as causal elasticity. The simulator requires an explicit analyst assumption instead.</p>
      </Panel>

      <Panel title="AI decision brief" subtitle="A narrative layer with hard boundaries around the analytical result">
        <div className="ai-method-grid">
          <article><span>01</span><div><strong>Server calculation</strong><p>The API reloads the published route record and recomputes the scenario with the same tested Python equations.</p></div></article>
          <article><span>02</span><div><strong>Structured generation</strong><p>Claude returns a fixed schema containing a headline, approved evidence keys, approved risk keys, and a next step.</p></div></article>
          <article><span>03</span><div><strong>Policy validation</strong><p>The server rejects changed recommendations, unsupported evidence, numbers in generated prose, and profit or causal claims.</p></div></article>
          <article><Sparkles size={18}/><div><strong>Human review</strong><p>The output is labeled AI-generated and remains a draft. It cannot publish a fare, change inventory, or replace analyst approval.</p></div></article>
        </div>
        <p className="formula-note">Evaluation cases cover supported changes, extrapolation, capacity constraints, competitor response, optional cost, schema validity, and prohibited claims. Exact calculations remain outside the language model.</p>
      </Panel>

      <Panel title="Model risk register" subtitle="Known gaps remain visible instead of being filled with invented data">
        <div className="table-scroll"><table className="risk-table"><thead><tr><th>Risk</th><th>Why it matters</th><th>Control</th></tr></thead><tbody>
          <tr><td>Fare endogeneity</td><td>Airlines respond to demand information that the public model cannot observe.</td><td>Reject the nonnegative estimates, make no causal claim, and keep scenario elasticity analyst supplied.</td></tr>
          <tr><td>Survey transition</td><td>DB1B and DB1C have different frequency and sample rates.</td><td>Maintain separate marts and document bridge behavior before combined reporting.</td></tr>
          <tr><td>Carrier mapping</td><td>Reporting and operating carriers can differ across sources and time.</td><td>Use a dated bridge, publish join coverage, and quarantine ambiguous keys.</td></tr>
          <tr><td>No route cost</td><td>Revenue improvement does not prove profit improvement.</td><td>Do not report historical profit. Accept optional user cost only in a scenario.</td></tr>
          <tr><td>Thin markets</td><td>Limited fare variation produces unstable estimates.</td><td>Require minimum history and variation, widen uncertainty, and suppress rankings.</td></tr>
        </tbody></table></div>
      </Panel>

      <section className="source-section"><h2>Primary sources</h2><div className="source-grid">
        <a href="https://www.bts.gov/topics/airlines-and-airports/origin-and-destination-survey-data" target="_blank" rel="noreferrer"><span>U.S. DOT</span><strong>Origin and Destination Survey</strong><small>DB1B and DB1C collection transition</small></a>
        <a href="https://www.transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EEE" target="_blank" rel="noreferrer"><span>U.S. DOT</span><strong>T-100 database profile</strong><small>Traffic, capacity, coverage, and terms</small></a>
        <a href="https://www.bts.gov/air-fares" target="_blank" rel="noreferrer"><span>U.S. DOT</span><strong>Air fare definitions</strong><small>Ticket value and exclusions</small></a>
        <a href="https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html" target="_blank" rel="noreferrer"><span>scikit-learn</span><strong>Time-ordered validation</strong><small>Forecast split implementation reference</small></a>
        <a href="https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools" target="_blank" rel="noreferrer"><span>Anthropic</span><strong>Structured tool output</strong><small>Strict schema and forced tool reference</small></a>
      </div></section>
    </div>
  );
}
