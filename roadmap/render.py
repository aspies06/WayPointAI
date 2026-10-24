"""Turns a Roadmap into the response a user reads: Markdown, so Streamlit's
st.markdown() and a terminal both show it. Most important work comes first,
every step has dates at the user's own pace, and every resource has its link.
"""
from datetime import date

from .schemas import BENEFIT_LABELS, PRIORITY_LABELS, Roadmap, Step


def _d(d: date) -> str:
    return f"{d:%b} {d.day}, {d.year}"


DISCLAIMER = ("*{kind} guidance. It can make mistakes, so check dates, prices and requirements "
              "with each provider before you rely on them.*")
LISTINGS_CREDIT = ("*AI/ML Engineer skills: share of junior and mid-level ML engineer job listings on AI Dev "
                   "Jobs (aidevboard.com) asking for each skill.*")
CREDIT = ("*Prices are approximate and can change. Skill data includes information from the O*NET 31.0 "
          "Database by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), "
          "used under the CC BY 4.0 license. O*NET® is a trademark of USDOL/ETA.*")


def _cost(c: int) -> str:
    return "free" if c == 0 else f"about ${c}"


def _step(s: Step, gaps: dict[str, str]) -> list[str]:
    when = f"{_d(s.start_date)} → {_d(s.end_date)}" if s.start_date else "whenever you're ready"
    out = [f"#### {s.step_id}. {s.title}",
           f"*{when} · about {s.est_hours} hours · {_cost(s.cost_usd)} · {BENEFIT_LABELS[s.benefit]}*", ""]
    if s.scope_note:
        out += [f"> {s.scope_note}", ""]
    out.append(f"- **Why:** {s.why}")
    if gaps:
        out.append(f"- **Closes:** {', '.join(gaps.get(g, g) for g in s.gap_ids)}")
    out += [f"- **Deliver:** {s.deliverable}", f"- **Done when:** {s.done_when}"]
    if s.tip:
        out.append(f"- **Tip:** {s.tip}")
    if s.resources:
        out.append("- **Sources:**")
        out += [f"  - [{r.name}]({r.url}) ({r.provider}, {_cost(r.cost_usd)})" for r in s.resources]
    if s.suggestions:
        out.append("- **Worth considering:**")
        out += [f"  - {x.reason}" + (f" ([details]({x.resource.url}))" if x.resource else "")
                for x in s.suggestions]
    return out + [""]


def optional_count(roadmap: Roadmap) -> int:
    """How many things are off the timeline; the UI's "show optional" button can show this number."""
    return len(roadmap.optional) + len(_uncovered(roadmap))


def _uncovered(roadmap: Roadmap):
    """Deferred gaps with no optional item behind them (nothing in the catalog yet)."""
    kept = {g for s in roadmap.optional for g in s.gap_ids}
    if roadmap.experience:
        kept.add(roadmap.experience.gap_id)  # shown at the top instead
    return [d for d in roadmap.deferred if d.gap_id not in kept]


def timeline_markdown(roadmap: Roadmap, gap_names: dict[str, str] | None = None) -> str:
    """The user's plan: pace, timeline table and steps by priority. Nothing optional."""
    gaps = gap_names or {}
    r = roadmap
    fits = r.finish_date <= r.target_date
    out = [f"## Your {r.target_role.title} roadmap", f"`{r.label}`", "", r.summary, "",
           f"**Your pace:** {r.hours_per_week} hours/week, starting {_d(r.start_date)}. "
           f"Planned work ({r.total_hours} hours) finishes **{_d(r.finish_date)}**, "
           + (f"ahead of your {_d(r.target_date)} target." if fits else
              f"after your {_d(r.target_date)} target."), ""]
    if r.experience:
        out += [f"> **Most important:** {r.experience.message}", ""]

    if r.steps:
        out += ["### Timeline", "", "| Step | Priority | Dates | Hours |", "|---|---|---|---|"]
        out += [f"| {s.step_id}. {s.title} | {PRIORITY_LABELS[s.priority]} | "
                f"{_d(s.start_date)} → {_d(s.end_date)} | {s.est_hours} |" for s in r.steps]
        out.append("")

    for pri, label in PRIORITY_LABELS.items():
        steps = [s for s in r.steps if s.priority == pri]
        if steps:
            out += [f"### {label}", ""]
            for s in steps:
                out += _step(s, gaps)

    if r.warnings:
        out += ["> " + w for w in r.warnings] + [""]
    return "\n".join(out)


def optional_markdown(roadmap: Roadmap, gap_names: dict[str, str] | None = None) -> str:
    """Everything kept off the timeline, for the UI to show behind a button. Empty if there is none."""
    gaps = gap_names or {}
    r = roadmap
    out: list[str] = []
    sections = [("time", "If you get more time",
                 "These don't fit before your target date at your current pace, or they're the rest of a step "
                 "that was shortened to fit."),
                ("budget", "If you can spend more",
                 "These go over what you wanted to spend. Some may still be worth it; see the notes.")]
    for because, title, intro in sections:
        items = [s for s in r.optional if s.optional_because == because]
        if items:
            out += [f"### {title}", "", intro, ""]
            for s in items:
                out += _step(s, gaps)
    if (uncovered := _uncovered(r)):
        out += ["### Not covered yet", ""]
        out += [f"- **{gaps.get(d.gap_id, d.gap_id)}:** {d.reason}" for d in uncovered]
        out.append("")
    return "\n".join(out)


def to_markdown(roadmap: Roadmap, gap_names: dict[str, str] | None = None,
                include_optional: bool = True) -> str:
    """The whole response as one page (CLI, email). A UI should use timeline_markdown()
    and put optional_markdown() behind a button instead; see roadmap/ui.py."""
    kind = "Automatically generated" if roadmap.source == "basic" else "AI-generated"
    parts = [DISCLAIMER.format(kind=kind), "", timeline_markdown(roadmap, gap_names)]
    if include_optional and (extra := optional_markdown(roadmap, gap_names)):
        parts += ["---", "## Optional", "", extra]
    if roadmap.target_role.role == "AI/ML Engineer":  # its skills come from job listings, not O*NET
        parts += ["", LISTINGS_CREDIT]
    return "\n".join(parts + ["", CREDIT])
