"""Builds the roadmap from the catalog with plain rules. No model involved.

Each gap maps to a project template if one matches, otherwise to catalog
resources. Gaps that don't fit the hours or budget, or have nothing in the
catalog, are deferred with a reason so nothing silently disappears.
The local model only adds tips on top of this (see personalize.py), so the
plan itself is always grounded and always the same for the same input.
"""
import re
from datetime import date
from typing import Optional

from . import catalog
from .guardrails import available_hours
from .schemas import Deferred, GapList, RoadmapDraft, Step, TargetRole

SEV_ORDER = {"high": 0, "medium": 1, "low": 2}
DEFAULT_CERT_HOURS = 30
DEFAULT_COURSE_HOURS = 8


def _phase(hours_before: int, hours_per_week: int) -> str:
    weeks = hours_before / hours_per_week
    if weeks < 30 / 7:
        return "first_30_days"
    if weeks < 90 / 7:
        return "days_30_90"
    return "days_90_plus"


def _clean(text: str) -> str:
    """Gap text comes from other systems; never echo links from it."""
    return re.sub(r"\s+", " ", re.sub(r"\S*(https?://|www\.)\S*", "", text)).strip()


def _step_for(gap, target: TargetRole, n: int) -> Optional[Step]:
    why = f"{gap.peer_share}% of {target.title} hires have {_clean(gap.item)} ({gap.severity} priority)."
    res = catalog.resources_for(gap.item, target.level, target.role)
    proj = catalog.projects_for(gap.item, target.level, target.role)

    if gap.category == "cert" and res:
        exams = [r for r in res if r["type"] == "cert"]
        courses = [r for r in res if r["type"] == "course"]
        if exams:
            hours = sum(r["hours"] for r in exams + courses) or DEFAULT_CERT_HOURS
            return Step(
                step_id=f"S{n}", title=f"Pass {exams[0]['name']}", phase="first_30_days",
                type="cert", gap_ids=[gap.gap_id], why=why,
                deliverable=f"{exams[0]['name']} passed and listed in the Certifications section of your resume",
                done_when="You have the pass score report and the credential ID is on your resume",
                resource_ids=[r["id"] for r in courses[:1] + exams[:1]],
                est_hours=hours, depends_on=[])

    if proj:
        p = proj[0]
        return Step(
            step_id=f"S{n}", title=p["title"], phase="first_30_days", type="project",
            gap_ids=[gap.gap_id], why=why, deliverable=p["deliverable"], done_when=p["done_when"],
            resource_ids=[r for r in p["resource_ids"] if r in catalog.resources()],
            project_id=p["id"], est_hours=p["est_hours"], depends_on=[])

    if res:
        # "Complete <free trial account>" isn't a step; pick something you learn from.
        r = next((x for x in res if x["type"] not in ("tool", "community")), res[0])
        return Step(
            step_id=f"S{n}", title=f"Complete {r['name']}", phase="first_30_days", type="course",
            gap_ids=[gap.gap_id], why=why,
            deliverable=f"Completion record for {r['name']} plus one resume bullet showing how you used {_clean(gap.item)}",
            done_when="Completion screenshot or certificate saved and the resume bullet is added",
            resource_ids=[r["id"]], est_hours=r["hours"] or DEFAULT_COURSE_HOURS, depends_on=[])
    return None


def build_plan(gap_list: GapList, today: Optional[date] = None) -> RoadmapDraft:
    role = gap_list.target_role.title
    hpw = gap_list.user_context.hours_per_week
    budget_hours = available_hours(gap_list, today)
    gaps = sorted(gap_list.gaps, key=lambda g: (SEV_ORDER[g.severity], -g.peer_share))

    steps: list[Step] = []
    deferred: list[Deferred] = []
    by_project: dict[str, Step] = {}
    used = 0
    paid: set[str] = set()
    budget = gap_list.user_context.budget_usd
    cost = lambda ids: sum(catalog.resources()[r]["cost_usd"] for r in ids)

    for gap in gaps:
        step = _step_for(gap, gap_list.target_role, len(steps) + 1)
        if step is None:
            deferred.append(Deferred(gap_id=gap.gap_id,
                                     reason="No curated resource or project for this gap yet; ask a mentor or add one to the catalog."))
            continue
        if step.project_id and step.project_id in by_project:
            by_project[step.project_id].gap_ids.append(gap.gap_id)  # one project closes both gaps
            continue
        if used + step.est_hours > budget_hours:
            deferred.append(Deferred(gap_id=gap.gap_id,
                                     reason=f"Needs about {step.est_hours} hours, which doesn't fit before the target date at {hpw} hours/week."))
            continue
        new_paid = set(step.resource_ids) - paid
        if cost(paid | new_paid) > budget and cost(new_paid) > 0:
            deferred.append(Deferred(gap_id=gap.gap_id,
                                     reason=f"Costs about ${cost(new_paid)}, which goes over your ${budget} budget."))
            continue
        paid |= new_paid
        step.phase = _phase(used, hpw)
        used += step.est_hours
        steps.append(step)
        if step.project_id:
            by_project[step.project_id] = step

    if not gap_list.gaps:
        return RoadmapDraft(summary=f"You already match what most {role} hires have. No gaps to close.",
                            steps=[], deferred=[])
    n_high = sum(1 for g in gap_list.gaps if g.severity == "high")
    summary = (f"Your {role} roadmap: {len(steps)} steps, most common gaps first"
               f" ({n_high} high priority), about {used} hours total.")
    if deferred:
        summary += f" {len(deferred)} gap(s) are deferred with reasons."
    return RoadmapDraft(summary=summary, steps=steps, deferred=deferred)
