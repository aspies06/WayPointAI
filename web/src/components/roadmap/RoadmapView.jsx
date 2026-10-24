import { useState } from "react";
import { PRIORITY_LABELS, formatCost, formatDate } from "../../lib/format.js";
import { StepCard } from "./StepCard.jsx";

const OPTIONAL_SECTIONS = [
  {
    because: "time",
    title: "If you get more time",
    intro: "These don't fit before your target date at your pace, or they're the rest of a step that was shortened to fit.",
  },
  {
    because: "budget",
    title: "If you can spend more",
    intro: "These are over your budget. Where the catalog has one, a free alternative is listed.",
  },
];

export function RoadmapView({ roadmap, gapNames }) {
  const [showOptional, setShowOptional] = useState(false);
  const kept = new Set(roadmap.optional.flatMap((s) => s.gap_ids));
  if (roadmap.experience) kept.add(roadmap.experience.gap_id); // shown at the top instead
  const uncovered = roadmap.deferred.filter((d) => !kept.has(d.gap_id));
  const optionalCount = roadmap.optional.length + uncovered.length;
  const onTime = roadmap.finish_date <= roadmap.target_date; // ISO dates compare as strings
  const spent = roadmap.steps.reduce((sum, s) => sum + s.cost_usd, 0);

  return (
    <article className="roadmap">
      <p className="disclaimer" role="note">
        {roadmap.source === "basic" ? "Automatically generated" : "AI-generated"} guidance. It can make
        mistakes, so check dates, prices and requirements with each provider before you rely on them.
      </p>
      <header className="roadmap-head">
        <div>
          <h2>Your {roadmap.target_role.title} roadmap</h2>
          <span className={"tag" + (roadmap.source === "basic" ? "" : " tag-ai")}>{roadmap.label}</span>
        </div>
        <p>{roadmap.summary}</p>
      </header>

      <dl className="stats">
        <div>
          <dt>Your pace</dt>
          <dd>{roadmap.hours_per_week} hours/week</dd>
        </div>
        <div>
          <dt>Starts</dt>
          <dd>{formatDate(roadmap.start_date)}</dd>
        </div>
        <div>
          <dt>Finishes</dt>
          <dd className={onTime ? "good" : "warn"}>{formatDate(roadmap.finish_date)}</dd>
        </div>
        <div>
          <dt>Your target</dt>
          <dd>{formatDate(roadmap.target_date)}</dd>
        </div>
        <div>
          <dt>Planned work</dt>
          <dd>{roadmap.total_hours} hours</dd>
        </div>
        <div>
          <dt>Approximate cost</dt>
          <dd>{spent ? "about " : ""}{formatCost(spent)}</dd>
        </div>
      </dl>

      {roadmap.experience && (
        <aside className="experience" aria-label="Most important">
          <strong>Most important</strong>
          <p>{roadmap.experience.message}</p>
        </aside>
      )}

      {roadmap.warnings.map((w) => (
        <p key={w} className="alert alert-warn">
          {w}
        </p>
      ))}

      {roadmap.steps.length > 0 && (
        <div className="table-scroll">
          <table className="timeline">
            <caption>Timeline</caption>
            <thead>
              <tr>
                <th>Step</th>
                <th>Priority</th>
                <th>Dates</th>
                <th>Hours</th>
              </tr>
            </thead>
            <tbody>
              {roadmap.steps.map((s) => (
                <tr key={s.step_id}>
                  <td>
                    <a href={"#" + s.step_id}>
                      {s.step_id}. {s.title}
                    </a>
                  </td>
                  <td>
                    <span className={"pill pill-" + s.priority}>{PRIORITY_LABELS[s.priority]}</span>
                  </td>
                  <td className="nowrap">
                    {formatDate(s.start_date)} → {formatDate(s.end_date)}
                  </td>
                  <td>{s.est_hours}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {Object.entries(PRIORITY_LABELS).map(([priority, label]) => {
        const steps = roadmap.steps.filter((s) => s.priority === priority);
        return (
          steps.length > 0 && (
            <section key={priority} className="priority-group">
              <h3>{label}</h3>
              {steps.map((s) => (
                <StepCard key={s.step_id} step={s} gapNames={gapNames} />
              ))}
            </section>
          )
        );
      })}

      {optionalCount > 0 && (
        <div className="optional-toggle">
          <button
            type="button"
            className="secondary"
            aria-expanded={showOptional}
            aria-controls="optional-items"
            onClick={() => setShowOptional(!showOptional)}
          >
            {showOptional ? "Hide" : "Show"} optional items ({optionalCount})
          </button>
          <span className="muted">
            Things that didn't fit your time or budget, kept here in case your plans change.
          </span>
        </div>
      )}

      {showOptional && (
        <section id="optional-items" className="optional">
          {OPTIONAL_SECTIONS.map(({ because, title, intro }) => {
            const items = roadmap.optional.filter((s) => s.optional_because === because);
            return (
              items.length > 0 && (
                <section key={because} className="priority-group">
                  <h3>{title}</h3>
                  <p className="muted">{intro}</p>
                  {items.map((s) => (
                    <StepCard key={s.step_id} step={s} gapNames={gapNames} />
                  ))}
                </section>
              )
            );
          })}
          {uncovered.length > 0 && (
            <section className="priority-group">
              <h3>Not covered yet</h3>
              <ul className="plain">
                {uncovered.map((d) => (
                  <li key={d.gap_id}>
                    <strong>{gapNames[d.gap_id] || d.gap_id}:</strong> {d.reason}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </section>
      )}

      <p className="credit">
        Prices are approximate and can change; check the provider's site. Skill data includes information
        from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration
        (USDOL/ETA), used under the CC BY 4.0 license. O*NET® is a trademark of USDOL/ETA.
        {roadmap.target_role.role === "AI/ML Engineer" &&
          " AI/ML Engineer skills: share of junior and mid-level ML engineer job listings on AI Dev Jobs (aidevboard.com) asking for each skill."}
      </p>
    </article>
  );
}
