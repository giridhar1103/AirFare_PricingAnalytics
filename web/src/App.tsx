import { lazy, Suspense, useEffect, useState } from "react";
import { Redirect, Route, Switch } from "wouter";
import { AppShell } from "./components/AppShell";
import { FixtureNotice } from "./components/FixtureNotice";
import type { OverviewArtifact } from "./data/types";

const OverviewPage = lazy(() => import("./pages/OverviewPage").then((module) => ({ default: module.OverviewPage })));
const MarketsPage = lazy(() => import("./pages/MarketsPage").then((module) => ({ default: module.MarketsPage })));
const ModelLabPage = lazy(() => import("./pages/ModelLabPage").then((module) => ({ default: module.ModelLabPage })));
const ScenarioPage = lazy(() => import("./pages/ScenarioPage").then((module) => ({ default: module.ScenarioPage })));
const MethodologyPage = lazy(() => import("./pages/MethodologyPage").then((module) => ({ default: module.MethodologyPage })));

function App() {
  const [artifact, setArtifact] = useState<OverviewArtifact | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/farelab-overview.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`Data request failed with status ${response.status}`);
        return response.json();
      })
      .then(setArtifact)
      .catch((reason: Error) => setError(reason.message));
  }, []);

  if (error) {
    return <div className="load-state"><strong>FareLab could not load its analytical artifact.</strong><span>{error}</span></div>;
  }
  if (!artifact) {
    return <div className="load-state"><div className="loading-mark" /><span>Loading FareLab workspace</span></div>;
  }

  const isFixture = artifact.data_mode === "development_fixture";
  return (
    <AppShell isFixture={isFixture} sourceVintage={artifact.source_vintage}>
      {isFixture && <FixtureNotice notice={artifact.notice} />}
      <Suspense fallback={<div className="section-load-state">Loading analysis</div>}>
        <Switch>
          <Route path="/"><OverviewPage artifact={artifact} /></Route>
          <Route path="/markets"><MarketsPage routes={artifact.routes} /></Route>
          <Route path="/models"><ModelLabPage artifact={artifact} /></Route>
          <Route path="/elasticity"><Redirect to="/models" /></Route>
          <Route path="/scenario"><ScenarioPage routes={artifact.routes} /></Route>
          <Route path="/methodology"><MethodologyPage artifact={artifact} /></Route>
          <Route><Redirect to="/" /></Route>
        </Switch>
      </Suspense>
    </AppShell>
  );
}

export default App;
