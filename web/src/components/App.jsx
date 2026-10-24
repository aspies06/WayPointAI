import { useEffect, useState } from "react";
import { getOptions, getRoadmaps } from "../api.js";
import { PlannerForm } from "./PlannerForm.jsx";
import { Results } from "./Results.jsx";
import { Brand } from "./Brand.jsx";
import { ResumeBuilder } from "./ResumeBuilder.jsx";

export function App() {
  const [view, setView] = useState("roadmap");
  const [options, setOptions] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

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
            Plan your next career step, capture the experience you already have, and build a
            resume that tells your story.
          </p>
        </div>
      </header>
      <main className="wrap">
        <nav className="tabs workspace-tabs" aria-label="Career tools">
          <button
            type="button"
            className={"tab" + (view === "roadmap" ? " tab-on" : "")}
            aria-pressed={view === "roadmap"}
            onClick={() => setView("roadmap")}
          >
            Career roadmap
          </button>
          <button
            type="button"
            className={"tab" + (view === "resume" ? " tab-on" : "")}
            aria-pressed={view === "resume"}
            onClick={() => setView("resume")}
          >
            Resume builder
          </button>
        </nav>
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
          <ResumeBuilder roles={options?.roles || []} />
        </div>
      </main>
      <footer className="site-footer wrap muted">
        Uploaded resumes for roadmaps aren't stored. Stories you choose to save are stored on the
        computer running WayPointAI, and you can edit or delete them in your story bank.
      </footer>
    </>
  );
}
