import { BENEFIT_LABELS, formatCost, formatDate } from "../format.js";

/** One roadmap step: what to do, why, how you'll know you're done, and where to learn it.
 *  Every link comes from the checked catalog via the API, never from user text. */
export function StepCard({ step, gapNames }) {
  const when = step.start_date
    ? `${formatDate(step.start_date)} → ${formatDate(step.end_date)}`
    : "Whenever you're ready";
  const closes = step.gap_ids.map((g) => gapNames[g]).filter(Boolean);

  return (
    <article className="step" id={step.step_id}>
      <header>
        <h4>
          {step.step_id}. {step.title}
        </h4>
        <div className="meta">
          <span>{when}</span>
          <span>about {step.est_hours} hours</span>
          <span>{step.cost_usd ? "about " : ""}{formatCost(step.cost_usd)}</span>
          <span className={"badge badge-" + step.benefit}>{BENEFIT_LABELS[step.benefit]}</span>
        </div>
      </header>
      {step.scope_note && <p className="note">{step.scope_note}</p>}
      <dl className="step-body">
        <dt>Why</dt>
        <dd>{step.why}</dd>
        {closes.length > 0 && (
          <>
            <dt>Closes</dt>
            <dd>{closes.join(", ")}</dd>
          </>
        )}
        <dt>Deliver</dt>
        <dd>{step.deliverable}</dd>
        <dt>Done when</dt>
        <dd>{step.done_when}</dd>
        {step.tip && (
          <>
            <dt>Tip</dt>
            <dd>{step.tip}</dd>
          </>
        )}
      </dl>
      {step.resources.length > 0 && (
        <div className="sources">
          <h5>Sources</h5>
          <ul className="plain">
            {step.resources.map((r) => (
              <li key={r.id}>
                <a href={r.url} target="_blank" rel="noopener noreferrer">
                  {r.name}
                </a>
                <span className="muted">
                  {" "}
                  · {r.provider} · {r.cost_usd ? "about " : ""}{formatCost(r.cost_usd)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {step.suggestions.length > 0 && (
        <div className="worth">
          <h5>Worth considering</h5>
          <ul className="plain">
            {step.suggestions.map((s) => (
              <li key={s.kind + s.resource_id}>
                {s.reason}
                {s.resource && (
                  <>
                    {" "}
                    <a href={s.resource.url} target="_blank" rel="noopener noreferrer">
                      Details
                    </a>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
