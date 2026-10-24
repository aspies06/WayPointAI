import { useEffect, useState } from "react";
import { html } from "../html.js";
import { getOptions, getRoadmaps } from "../api.js";
import { PlannerForm } from "./PlannerForm.js";
import { Results } from "./Results.js";
import { Brand } from "./Brand.js";

export function App() {
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

  return html`
    <header className="site-header">
      <div className="wrap">
        <${Brand} />
        <p className="tagline">
          Tell us where you are, where you want to go, and how much time you have. You'll get a
          roadmap with your most important work first, dates you can keep, and links to every
          resource.
        </p>
      </div>
    </header>
    <main className="wrap">
      ${loadError && html`<p className="alert alert-error" role="alert">${loadError}</p>`}
      ${!options && !loadError && html`<p className="muted">Loading…</p>`}
      ${options &&
      html`<${PlannerForm}
        options=${options}
        onSubmit=${handleSubmit}
        submitting=${submitting}
        error=${submitError}
      />`}
      ${result && html`<${Results} result=${result} />`}
    </main>
    <footer className="site-footer wrap muted">
      Your resume is read on this computer and isn't stored.
    </footer>
  `;
}
