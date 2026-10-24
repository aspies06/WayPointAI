import { useEffect, useState } from "react";
import { getOptions, getRoadmaps } from "../api.js";
import { PlannerForm } from "./PlannerForm.jsx";
import { Results } from "./Results.jsx";
import { Brand } from "./Brand.jsx";
import { ResumeBuilder } from "./ResumeBuilder.jsx";
import { PrivacyNotice } from "./PrivacyNotice.jsx";
import { ThemeSwitch } from "./ThemeSwitch.jsx";
import { applyTheme, onSystemThemeChange, saveTheme, savedTheme } from "../theme.js";

export function App() {
  const [view, setView] = useState("roadmap");
  const [themeChoice, setThemeChoice] = useState(savedTheme);

  useEffect(() => {
    applyTheme(themeChoice);
    if (themeChoice !== "system") return undefined;
    return onSystemThemeChange(() => applyTheme("system"));
  }, [themeChoice]);

  function chooseTheme(choice) {
    saveTheme(choice);
    setThemeChoice(choice);
  }
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
          <ThemeSwitch choice={themeChoice} onChange={chooseTheme} />
          <Brand />
          <p className="tagline">
            Plan your next career step, capture the experience you already have, and build a
            resume that tells your story.
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
          <ResumeBuilder roles={options?.roles || []} />
        </div>
      </main>
      <div className="wrap">
        <PrivacyNotice />
      </div>
      <footer className="site-footer wrap muted">
        <p className="slogan">Stored locally, never in the cloud.</p>
        <p>
          Uploaded resumes aren't stored. Stories you save stay encrypted in this browser on your device.{" "}
          <a href="#privacy">What's stored</a>
        </p>
      </footer>
    </>
  );
}
