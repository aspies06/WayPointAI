import { useState } from "react";
import { html } from "../html.js";
import { PRIORITY_LABELS, formatCost, formatDate } from "../format.js";
import { StepCard } from "./StepCard.js";

const OPTIONAL_SECTIONS = [
  {
    because: "time",
    title: "If you get more time",
    intro: "These don't fit before your target date at your pace, or they're the rest of a step that was shortened to fit.",
  },
  {
    because: "budget",
    title: "If you can spend more",
    intro: "These go over what you wanted to spend. Some may still be worth it; see the notes.",
  },
];

export function RoadmapView({ roadmap, gapNames }) {
  const [showOptional, setShowOptional] = useState(false);
  const kept = new Set(roadmap.optional.flatMap((s) => s.gap_ids));
  const uncovered = roadmap.deferred.filter((d) => !kept.has(d.gap_id));
  const optionalCount = roadmap.optional.length + uncovered.length;
  const onTime = roadmap.finish_date <= roadmap.target_date; // ISO dates compare as strings
  const spent = roadmap.steps.reduce((sum, s) => sum + s.cost_usd, 0);

  return html`
    <article className="roadmap">
      <header className="roadmap-head">
        <div>
          <h2>Your ${roadmap.target_role.title} roadmap</h2>
          <span className=${"tag" + (roadmap.source === "basic" ? "" : " tag-ai")}>${roadmap.label}</span>
        </div>
        <p>${roadmap.summary}</p>
      </header>

      <dl className="stats">
        <div><dt>Your pace</dt><dd>${roadmap.hours_per_week} hours/week</dd></div>
        <div><dt>Starts</dt><dd>${formatDate(roadmap.start_date)}</dd></div>
        <div>
          <dt>Finishes</dt>
          <dd className=${onTime ? "good" : "warn"}>${formatDate(roadmap.finish_date)}</dd>
        </div>
        <div><dt>Your target</dt><dd>${formatDate(roadmap.target_date)}</dd></div>
        <div><dt>Planned work</dt><dd>${roadmap.total_hours} hours</dd></div>
        <div><dt>Cost</dt><dd>${formatCost(spent)}</dd></div>
      </dl>

      ${roadmap.warnings.map((w) => html`<p key=${w} className="alert alert-warn">${w}</p>`)}

      ${roadmap.steps.length > 0 &&
      html`<div className="table-scroll">
        <table className="timeline">
          <caption>Timeline</caption>
          <thead><tr><th>Step</th><th>Priority</th><th>Dates</th><th>Hours</th></tr></thead>
          <tbody>
            ${roadmap.steps.map(
              (s) => html`<tr key=${s.step_id}>
                <td><a href=${"#" + s.step_id}>${s.step_id}. ${s.title}</a></td>
                <td><span className=${"pill pill-" + s.priority}>${PRIORITY_LABELS[s.priority]}</span></td>
                <td className="nowrap">${formatDate(s.start_date)} → ${formatDate(s.end_date)}</td>
                <td>${s.est_hours}</td>
              </tr>`
            )}
          </tbody>
        </table>
      </div>`}

      ${Object.entries(PRIORITY_LABELS).map(([priority, label]) => {
        const steps = roadmap.steps.filter((s) => s.priority === priority);
        return (
          steps.length > 0 &&
          html`<section key=${priority} className="priority-group">
            <h3>${label}</h3>
            ${steps.map((s) => html`<${StepCard} key=${s.step_id} step=${s} gapNames=${gapNames} />`)}
          </section>`
        );
      })}

      ${optionalCount > 0 &&
      html`<div className="optional-toggle">
        <button
          type="button"
          className="secondary"
          aria-expanded=${showOptional}
          aria-controls="optional-items"
          onClick=${() => setShowOptional(!showOptional)}
        >
          ${showOptional ? "Hide" : "Show"} optional items (${optionalCount})
        </button>
        <span className="muted">Things that didn't fit your time or budget, kept here in case your plans change.</span>
      </div>`}

      ${showOptional &&
      html`<section id="optional-items" className="optional">
        ${OPTIONAL_SECTIONS.map(({ because, title, intro }) => {
          const items = roadmap.optional.filter((s) => s.optional_because === because);
          return (
            items.length > 0 &&
            html`<section key=${because} className="priority-group">
              <h3>${title}</h3>
              <p className="muted">${intro}</p>
              ${items.map((s) => html`<${StepCard} key=${s.step_id} step=${s} gapNames=${gapNames} />`)}
            </section>`
          );
        })}
        ${uncovered.length > 0 &&
        html`<section className="priority-group">
          <h3>Not covered yet</h3>
          <ul className="plain">
            ${uncovered.map(
              (d) => html`<li key=${d.gap_id}><strong>${gapNames[d.gap_id] || d.gap_id}:</strong> ${d.reason}</li>`
            )}
          </ul>
        </section>`}
      </section>`}
    </article>
  `;
}
