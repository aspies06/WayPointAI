/** What people in a role do and the technologies in demand for it, from O*NET, with the source.
 *  After a draft is built, each technology also shows whether the saved stories mention it. */
export function RoleInsights({ insights }) {
  const { people_in_role: people, in_demand_technologies: technologies } = insights;
  const checked = technologies.some((t) => "in_your_stories" in t);

  return (
    <div className="role-insights">
      <div className="insight-column">
        <h3>What people in this job do</h3>
        <p className="hint">
          Tasks rated most important by people who work as {people.occupation}
          {people.match === "approximate" ? " (the closest occupation O*NET tracks)" : ""}.
        </p>
        <ul className="insight-tasks">
          {people.tasks.map((task) => <li key={task}>{task}</li>)}
        </ul>
      </div>
      <div className="insight-column">
        <h3>Technologies in demand</h3>
        <p className="hint">
          Technologies O*NET flags as in demand for this occupation: often listed in employer job postings.
        </p>
        {technologies.length ? (
          <ul className="insight-skills">
            {technologies.map((t) => (
              <li key={t.name} className={checked ? (t.in_your_stories ? "found" : "missing") : ""}>
                <span>{t.name}</span>
                {checked && <span className="mark">{t.in_your_stories ? "In your stories" : "Not in your stories yet"}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="hint">O*NET doesn't flag specific technologies for this occupation.</p>
        )}
        {checked && (
          <p className="hint">
            Missing something you've actually used? Add a story about it. Technologies are never added to your resume on
            your behalf.
          </p>
        )}
      </div>
      <p className="insight-sources">{insights.sources.join(" ")}</p>
    </div>
  );
}
