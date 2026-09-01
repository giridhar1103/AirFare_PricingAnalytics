import { FileText, LoaderCircle, ShieldCheck, Sparkles, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  generateDecisionBrief,
  type DecisionBriefRequest,
  type DecisionBriefResponse
} from "../lib/decisionBrief";

interface AiDecisionBriefProps {
  request: DecisionBriefRequest;
}

export function AiDecisionBrief({ request }: AiDecisionBriefProps) {
  const [brief, setBrief] = useState<DecisionBriefResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const requestKey = JSON.stringify(request);
  const currentKey = useRef(requestKey);

  useEffect(() => {
    currentKey.current = requestKey;
    setBrief(null);
    setStatus("idle");
  }, [requestKey]);

  const generate = async () => {
    const submittedKey = requestKey;
    setStatus("loading");
    try {
      const response = await generateDecisionBrief(request);
      if (currentKey.current !== submittedKey) return;
      setBrief(response);
      setStatus("idle");
    } catch {
      if (currentKey.current !== submittedKey) return;
      setStatus("error");
    }
  };

  return (
    <section className="ai-brief" aria-labelledby="ai-brief-title">
      <div className="ai-brief-header">
        <div>
          <span className="ai-kicker"><Sparkles size={15}/>Grounded AI decision brief</span>
          <h2 id="ai-brief-title">Turn the scenario into a review-ready handoff.</h2>
          <p>FareLab recalculates every number on the server. Claude can organize approved evidence and risks, but it cannot change the scenario math or the governed recommendation.</p>
        </div>
        <button className="ai-generate-button" type="button" onClick={generate} disabled={status === "loading"}>
          {status === "loading" ? <LoaderCircle className="spin-icon" size={17}/> : <FileText size={17}/>}
          {brief ? "Regenerate brief" : status === "loading" ? "Generating brief" : "Generate decision brief"}
        </button>
      </div>

      {!brief && status === "idle" && (
        <div className="ai-empty-state">
          <ShieldCheck size={20}/>
          <p><strong>Controlled scope</strong><span>No free-form prompt and no automated fare filing. The model receives one governed scenario record.</span></p>
        </div>
      )}
      {status === "error" && (
        <div className="ai-error" role="alert"><TriangleAlert size={18}/><span>The brief service is unavailable. The scenario calculation above is unaffected.</span></div>
      )}
      {brief && (
        <div className="ai-brief-output" aria-live="polite">
          <div className="ai-brief-lead">
            <span className={`ai-recommendation ai-recommendation-${brief.brief.recommendation.toLowerCase().replace(/ /g, "-")}`}>{brief.brief.recommendation}</span>
            <h3>{brief.brief.headline}</h3>
            <p>{brief.brief.summary}</p>
          </div>
          <div className="ai-brief-columns">
            <div><h4>Evidence selected</h4><ul>{brief.brief.evidence.map((item) => <li key={item}>{item}</li>)}</ul></div>
            <div><h4>Review risks</h4><ul>{brief.brief.risks.map((item) => <li key={item}>{item}</li>)}</ul></div>
          </div>
          <div className="ai-next-step"><span>Suggested next step</span><p>{brief.brief.nextStep}</p></div>
          <p className="ai-disclosure">AI-generated narrative from {brief.provider} {brief.model}. Calculations and recommendation policy are deterministic. Review before use.</p>
        </div>
      )}
    </section>
  );
}
