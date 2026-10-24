import { useEffect, useState } from "react";
import { getOptions, getRoadmaps } from "../api.js";
import { PlannerForm } from "./PlannerForm.jsx";
import { Results } from "./Results.jsx";
import { Brand } from "./Brand.jsx";
import { ResumeBuilder } from "./ResumeBuilder.jsx";

export function App() {
  const [options, setOptions] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [view, setView] = useState("roadmap");

  useEffect(() => {
    getOptions().then(setOptions, (error) => setLoadError(error.message));
  }, []);

  async function handleSubmit(form) {
    setSubmitting(true);
    setSubmitError("");
    try {
      setResult(await getRoadmaps(form));
      requestAnimationFrame(() =>
        document.getElementById("results")?.scrollIntoView({ behavior: "smooth" })
      );
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <header className="site-header">
        <div className="wrap">
          <Brand />
          <p className="tagline">
            Tell us where you are, where you want to go, and how much time you have. You'll get a
            roadmap with your most important work first, dates you can keep, and links to every
            resource.
          </p>
        </div>
      </header>
      <main className="wrap">
        <nav className="tabs workspace-tabs" aria-label="Career tools">
          {[["roadmap", "Career roadmap"], ["resume", "Resume builder"]].map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={"tab" + (view === id ? " tab-on" : "")}
              aria-pressed={view === id}
              onClick={() => setView(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        {/* Both stay mounted, so switching tabs keeps what you typed in either one. */}
        <div hidden={view !== "roadmap"}>
          {loadError && (
            <p className="alert alert-error" role="alert">
              {loadError}
            </p>
          )}
          {!options && !loadError && <p className="muted">Loading…</p>}
          {options && (
            <PlannerForm
              options={options}
              onSubmit={handleSubmit}
              submitting={submitting}
              error={submitError}
            />
          )}
          {result && <Results result={result} />}
        </div>
        <div hidden={view !== "resume"}>
          <ResumeBuilder />
        </div>
      </main>
      <footer className="site-footer wrap muted">
        Your resume is read on this computer and isn't stored.
      </footer>
    </>
  );
}
