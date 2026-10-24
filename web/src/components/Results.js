import { useState } from "react";
import { html } from "../html.js";
import { RoadmapView } from "./RoadmapView.js";

/** One tab per role the user picked. */
export function Results({ result }) {
  const [active, setActive] = useState(0);
  const { results, starting_from_scratch: fromScratch } = result;
  const current = results[Math.min(active, results.length - 1)];

  return html`
    <section id="results" className="results">
      ${fromScratch &&
      html`<p className="alert alert-info">
        No resume or skills were given, so these roadmaps assume you're starting from scratch.
      </p>`}
      ${results.length > 1 &&
      html`<div className="tabs" role="tablist">
        ${results.map(
          (r, i) => html`
            <button
              key=${r.role}
              type="button"
              role="tab"
              aria-selected=${i === active}
              className=${"tab" + (i === active ? " tab-on" : "")}
              onClick=${() => setActive(i)}
            >
              ${r.role}
            </button>
          `
        )}
      </div>`}
      <${RoadmapView} key=${current.role} roadmap=${current.roadmap} gapNames=${current.gap_names} />
    </section>
  `;
}
