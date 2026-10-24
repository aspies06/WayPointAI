import { useState } from "react";
import { html } from "../html.js";
import { maskDate } from "../format.js";

const EMPTY = {
  resume: null,
  skills: "",
  roles: [],
  level: "entry",
  experienceYears: "",
  workload: "",
  customHours: "",
  startDate: "",
  targetDate: "",
  budget: "",
  background: "",
};

/** What's still missing before we can plan. We ask about time first; we never guess it. */
function missingAnswers(form) {
  const missing = [];
  if (!form.roles.length) missing.push("pick at least one role");
  if (!form.workload) missing.push("choose how much time you can give each week");
  if (form.workload === "custom" && !form.customHours) missing.push("enter your hours per week");
  if (!form.targetDate) missing.push("say when you want to be ready");
  return missing;
}

export function PlannerForm({ options, onSubmit, submitting, error }) {
  const [form, setForm] = useState(EMPTY);
  const [triedSubmit, setTriedSubmit] = useState(false);
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value });
  const missing = missingAnswers(form);

  function toggleRole(role) {
    const roles = form.roles.includes(role)
      ? form.roles.filter((r) => r !== role)
      : [...form.roles, role];
    setForm({ ...form, roles });
  }

  function submit(event) {
    event.preventDefault();
    setTriedSubmit(true);
    if (!missing.length) onSubmit(form);
  }

  return html`
    <form className="planner" onSubmit=${submit} noValidate>
      <section className="card">
        <h2>Where you're starting</h2>
        <div className="grid two">
          <label className="field">
            <span className="label">Resume <span className="muted">(PDF or text, optional)</span></span>
            <input
              type="file"
              accept=".pdf,.txt"
              onChange=${(e) => setForm({ ...form, resume: e.target.files[0] || null })}
            />
          </label>
          <label className="field">
            <span className="label">No resume? Enter your skills <span className="muted">(optional)</span></span>
            <textarea
              rows="3"
              placeholder="For example: Python, SQL, Git, Excel. Leave blank to start from scratch."
              value=${form.skills}
              onChange=${set("skills")}
            ></textarea>
          </label>
        </div>
      </section>

      <section className="card">
        <h2>Where you're headed</h2>
        <fieldset className="field">
          <legend className="label">Roles you're interested in</legend>
          <div className="chips">
            ${options.roles.map(
              (role) => html`
                <button
                  type="button"
                  key=${role}
                  className=${"chip" + (form.roles.includes(role) ? " chip-on" : "")}
                  aria-pressed=${form.roles.includes(role)}
                  onClick=${() => toggleRole(role)}
                >
                  ${role}
                </button>
              `
            )}
          </div>
        </fieldset>
        <div className="grid two">
          <label className="field">
            <span className="label">Experience level you're aiming for</span>
            <select value=${form.level} onChange=${set("level")}>
              ${options.levels.map(
                (l) => html`<option key=${l.value} value=${l.value}>${l.label}</option>`
              )}
            </select>
          </label>
          <label className="field">
            <span className="label">Years of relevant experience</span>
            <input
              type="number"
              min="0"
              max="50"
              step="0.5"
              placeholder="0"
              value=${form.experienceYears}
              onChange=${set("experienceYears")}
            />
          </label>
        </div>
      </section>

      <section className="card card-accent">
        <h2>Your time <span className="required-note">We ask this first so the plan fits your life</span></h2>
        <fieldset className="field">
          <legend className="label">How much time can you give each week without burning out?</legend>
          <div className="workloads">
            ${[...options.workloads, { value: "custom", label: "Custom: I'll enter my own number" }].map(
              (w) => html`
                <label key=${w.value} className=${"workload" + (form.workload === w.value ? " workload-on" : "")}>
                  <input
                    type="radio"
                    name="workload"
                    value=${w.value}
                    checked=${form.workload === w.value}
                    onChange=${set("workload")}
                  />
                  <span>${w.label}</span>
                </label>
              `
            )}
          </div>
          ${form.workload === "custom" &&
          html`<label className="field inline">
            <span className="label">Hours per week</span>
            <input
              type="number"
              min="1"
              max="80"
              value=${form.customHours}
              onChange=${set("customHours")}
            />
          </label>`}
        </fieldset>
        <div className="grid three">
          <label className="field">
            <span className="label">When can you start? <span className="muted">(optional)</span></span>
            <input
              inputMode="numeric"
              placeholder="MM-DD-YYYY"
              value=${form.startDate}
              onChange=${(e) => setForm({ ...form, startDate: maskDate(e.target.value) })}
            />
            <span className="hint">Leave blank to start today.</span>
          </label>
          <label className="field">
            <span className="label">When do you want to be ready to apply?</span>
            <input
              inputMode="numeric"
              placeholder="MM-DD-YYYY"
              value=${form.targetDate}
              onChange=${(e) => setForm({ ...form, targetDate: maskDate(e.target.value) })}
            />
            <span className="hint">Or a number of weeks, like 12.</span>
          </label>
          <label className="field">
            <span className="label">Budget for courses, books and exams <span className="muted">(USD)</span></span>
            <input
              type="number"
              min="0"
              step="25"
              placeholder="No limit"
              value=${form.budget}
              onChange=${set("budget")}
            />
            <span className="hint">Any amount, including 0. Blank means no set limit.</span>
          </label>
        </div>
      </section>

      <section className="card">
        <label className="field">
          <span className="label">Anything else we should know? <span className="muted">(optional)</span></span>
          <textarea
            rows="2"
            maxLength="600"
            placeholder="Education, current work, or other useful context"
            value=${form.background}
            onChange=${set("background")}
          ></textarea>
        </label>
      </section>

      ${triedSubmit && missing.length > 0 &&
      html`<p className="alert alert-warn" role="alert">Before we can plan, please ${missing.join(", ")}.</p>`}
      ${error && html`<p className="alert alert-error" role="alert">${error}</p>`}

      <div className="actions">
        <button type="submit" className="primary" disabled=${submitting}>
          ${submitting ? "Building your roadmap…" : "Build my roadmap"}
        </button>
        ${submitting &&
        html`<span className="muted">With personal tips turned on, this can take up to a minute.</span>`}
      </div>
    </form>
  `;
}
