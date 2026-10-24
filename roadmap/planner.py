"""Builds the roadmap from the catalog with plain rules. No model involved.

1. Each gap becomes a step: a certification exam, a project template, or a
   resource to learn from, worded by what it earns (certification, certificate,
   portfolio piece, or knowledge only).
2. Budget: the plan stays within what the user wants to spend (no limit if they
   didn't say). A certification over budget becomes free exam prep, with the
   exam kept as an optional item. Other paid steps over budget become optional.
3. Time, by priority: must-do steps get time first, then should-do, then
   nice-to-have. If a tier doesn't fit, its biggest steps are shortened (and
   their remainder kept as an optional "part 2") so they stay at the front of
   the timeline; lower tiers move to optional rather than crowding them out.
4. Suggestions: each step may point out something worth considering, even over
   budget: a certification for the skill, a free alternative, a shorter course.

Gaps with nothing in the catalog are deferred with a reason, so nothing silently
disappears. The local model only adds tips on top (see personalize.py).
"""
import math
import re
from datetime import date, timedelta
from typing import Optional

from . import catalog
from .guardrails import available_hours, start_date
from .schemas import (PRIORITY_FROM_SEVERITY, SEV_RANK, Deferred, GapList, RoadmapDraft, Step, Suggestion,
                      TargetRole)

SEV_ORDER = SEV_RANK
DEFAULT_CERT_HOURS = 30
DEFAULT_COURSE_HOURS = 8
EXAM_HOURS = 3        # booking and sitting an exam once you've studied
MIN_PART_HOURS = 4    # a shortened step smaller than this isn't worth starting
TIERS = ("must_do", "should_do", "nice_to_have")
LEARNING_TYPES = ("course", "lab", "reference", "cert")


def _phase(hours_before: int, hours_per_week: int) -> str:
    weeks = hours_before / hours_per_week
    if weeks < 30 / 7:
        return "first_30_days"
    if weeks < 90 / 7:
        return "days_30_90"
    return "days_90_plus"


def _on_day(start: date, hours: int, hours_per_week: int) -> date:
    """The date `hours` of work is done, working steadily at hours_per_week from `start`."""
    return start + timedelta(days=math.ceil(hours * 7 / hours_per_week))


def _clean(text: str) -> str:
    """Gap text comes from other systems; never echo links from it."""
    return re.sub(r"\s+", " ", re.sub(r"\S*(https?://|www\.)\S*", "", text)).strip()


def _cert_step(exam: dict, courses: list[dict], **common) -> Step:
    return Step(**common, title=f"Pass {exam['name']}", type="cert", benefit="certification",
                deliverable=f"{exam['name']} passed and listed in the Certifications section of your resume",
                done_when="You have the pass score report and the credential ID is on your resume",
                resource_ids=[r["id"] for r in courses[:1] + [exam]],
                est_hours=sum(r["hours"] for r in [exam, *courses[:1]]) or DEFAULT_CERT_HOURS)


def _learn_step(r: dict, skill: str, **common) -> Step:
    """A step built on one resource, worded by what finishing it actually earns."""
    if r.get("credential") == "certification":
        return _cert_step(r, [], **common)
    if r.get("credential") == "certificate":
        return Step(**common, title=f"Complete {r['name']}", type="course", benefit="certificate",
                    deliverable=f"Certificate of completion for {r['name']}, plus one resume bullet showing how you used {skill}",
                    done_when="The certificate is saved or linked on your profile, and the resume bullet is added",
                    resource_ids=[r["id"]], est_hours=r["hours"] or DEFAULT_COURSE_HOURS)
    common["why"] += " There's no certificate for this one; the benefit is the knowledge itself."
    return Step(**common, title=f"Study {r['name']}", type="course", benefit="knowledge",
                deliverable=f"A short write-up or small exercise that applies {skill}, using {r['name']}, plus one resume bullet",
                done_when=f"You can explain the main ideas of {skill} without notes, and the exercise is saved in your portfolio",
                resource_ids=[r["id"]], est_hours=r["hours"] or DEFAULT_COURSE_HOURS)


def _step_for(gap, target: TargetRole) -> Optional[Step]:
    skill = _clean(gap.item)
    common = dict(step_id="S0", priority=PRIORITY_FROM_SEVERITY[gap.severity], phase="first_30_days",
                  gap_ids=[gap.gap_id], depends_on=[],
                  why=f"{gap.peer_share}% of {target.title} hires have {skill} ({gap.severity} priority).")
    res = catalog.resources_for(gap.item, target.level, target.role)
    proj = catalog.projects_for(gap.item, target.level, target.role)

    if gap.category == "cert":
        exams = [r for r in res if r.get("credential") == "certification"]
        if exams:
            return _cert_step(exams[0], [r for r in res if r["type"] == "course"], **common)
        if res or proj:
            common["why"] += " No certification for this is in our catalog, so this step builds the knowledge instead."

    if proj:
        p = proj[0]
        return Step(**common, title=p["title"], type="project", benefit="portfolio",
                    deliverable=p["deliverable"], done_when=p["done_when"],
                    resource_ids=[r for r in p["resource_ids"] if r in catalog.resources()],
                    project_id=p["id"], est_hours=p["est_hours"])
    if res:
        # "Complete <free trial account>" isn't a step; pick something you learn from.
        return _learn_step(next((x for x in res if x["type"] in LEARNING_TYPES), res[0]), skill, **common)
    return None


def _prep_step(step: Step, exam: dict) -> Optional[Step]:
    """The study half of a cert step, for when the exam is over budget."""
    courses = [catalog.resources()[r] for r in step.resource_ids if r != exam["id"]]
    if not courses:
        return None
    prep = step.model_copy(deep=True)
    prep.title = f"Prepare for {exam['name']}"
    prep.type = "course"
    prep.benefit = "certificate" if any(c.get("credential") == "certificate" for c in courses) else "knowledge"
    prep.resource_ids = [c["id"] for c in courses]
    prep.est_hours = sum(c["hours"] for c in courses) or DEFAULT_CERT_HOURS
    prep.deliverable = "Two practice-exam scores of 80% or higher, and notes on your weakest topics"
    prep.done_when = "You score 80%+ on two practice exams in a row, so you're ready to book the exam when you choose to"
    return prep


def _water_fill(hours: list[int], available: int) -> int:
    """The largest cap c with sum(min(h, c)) <= available: big steps shrink, small ones stay whole."""
    left, rest = available, sorted(hours)
    for i, h in enumerate(rest):
        if h * (len(rest) - i) <= left:
            left -= h
        else:
            return left // (len(rest) - i)
    return max(hours, default=0)


def _suggestions(step: Step, gap, target: TargetRole, budget_left: Optional[int]) -> list[Suggestion]:
    """At most two things worth considering. Budget is never a reason to hide a good option."""
    res = catalog.resources_for(gap.item, target.level, target.role)
    have = set(step.resource_ids)
    out: list[Suggestion] = []

    if step.benefit != "certification":
        cert = next((r for r in res if r.get("credential") == "certification" and r["id"] not in have), None)
        if cert:
            over = budget_left is not None and cert["cost_usd"] > budget_left
            out.append(Suggestion(kind="credential", resource_id=cert["id"], reason=(
                f"Turn this into a certification employers filter on: {cert['name']} (about ${cert['cost_usd']})."
                + (" It's over your budget, but a recognized certification can be worth stretching for." if over
                   else " It fits your budget."))))
    if step.cost_usd > 0:
        free = next((r for r in res if r["cost_usd"] == 0 and r["type"] in LEARNING_TYPES and r["id"] not in have), None)
        if free:
            out.append(Suggestion(kind="cheaper", resource_id=free["id"], reason=(
                f"Free alternative: {free['name']} covers the same ground and saves about ${step.cost_usd}.")))
    if step.type == "course" and step.est_hours >= 16:
        quick = next((r for r in res if r["type"] in LEARNING_TYPES and r["id"] not in have
                      and 0 < r["hours"] <= step.est_hours // 2), None)
        if quick:
            out.append(Suggestion(kind="faster", resource_id=quick["id"], reason=(
                f"Shorter option: {quick['name']} takes about {quick['hours']} hours instead of {step.est_hours}.")))
    return out[:2]


def build_plan(gap_list: GapList, today: Optional[date] = None) -> RoadmapDraft:
    role, ctx = gap_list.target_role, gap_list.user_context
    if not gap_list.gaps:
        return RoadmapDraft(summary=f"You already match what most {role.title} hires have. No gaps to close.",
                            steps=[], deferred=[])
    gaps = sorted(gap_list.gaps, key=lambda g: (SEV_ORDER[g.severity], -g.peer_share))
    gap_by_id = {g.gap_id: g for g in gaps}
    budget = ctx.budget_usd
    res = catalog.resources()
    cost = lambda ids: sum(res[r]["cost_usd"] for r in ids)
    deferred: list[Deferred] = []
    optional: list[Step] = []

    # 1. one step per gap; gaps sharing a project template share the step
    candidates: list[Step] = []
    by_project: dict[str, Step] = {}
    for gap in gaps:
        step = _step_for(gap, role)
        if step is None:
            deferred.append(Deferred(gap_id=gap.gap_id, reason=(
                "No curated resource or project for this gap yet; ask a mentor or add one to the catalog.")))
        elif step.project_id in by_project:
            by_project[step.project_id].gap_ids.append(gap.gap_id)  # keeps the first (higher) priority
        else:
            candidates.append(step)
            if step.project_id:
                by_project[step.project_id] = step

    def set_aside(step: Step, because: str, reason: str) -> None:
        step.optional_because = because
        optional.append(step)
        for g in step.gap_ids:
            deferred.append(Deferred(gap_id=g, reason=reason))

    # 2. budget, in priority order
    paid: set[str] = set()
    affordable: list[Step] = []
    for step in candidates:
        new = set(step.resource_ids) - paid
        if budget is None or cost(paid | new) <= budget or cost(new) == 0:
            paid |= new
            affordable.append(step)
            continue
        exam = next((res[r] for r in step.resource_ids if res[r].get("credential") == "certification"), None)
        prep = _prep_step(step, exam) if step.type == "cert" and exam else None
        if prep and cost(paid | set(prep.resource_ids)) <= budget:
            paid |= set(prep.resource_ids)
            prep.scope_note = (f"The exam itself (about ${exam['cost_usd']}) is over your ${budget} budget, so this step "
                               "covers the studying. The exam is kept in your optional items.")
            affordable.append(prep)
            exam_step = step.model_copy(update={"resource_ids": [exam["id"]], "est_hours": EXAM_HOURS})
            exam_step.optional_because = "budget"
            optional.append(exam_step)  # its gap is covered by the prep step on the timeline
        else:
            set_aside(step, "budget", f"Costs about ${cost(new)}, which goes over your ${budget} budget.")

    # 3. time, tier by tier: the first tier that doesn't fit is shortened, later tiers wait
    left = available_hours(gap_list, today)
    timeline: list[Step] = []
    for tier in TIERS:
        steps = [s for s in affordable if s.priority == tier]
        if not steps:
            continue
        if left <= 0:
            for s in steps:
                set_aside(s, "time", f"Needs about {s.est_hours} hours; your time before the target date goes to "
                                     "higher-priority steps first.")
            continue
        cap = max(_water_fill([s.est_hours for s in steps], left), MIN_PART_HOURS)
        for s in steps:
            part = min(s.est_hours, cap, left)
            if part < min(s.est_hours, MIN_PART_HOURS):
                set_aside(s, "time", f"Needs about {s.est_hours} hours; your time before the target date goes to "
                                     "higher-priority steps first.")
                continue
            if part < s.est_hours:
                rest = s.model_copy(deep=True)
                rest.title, rest.est_hours, rest.optional_because = f"{s.title} (part 2)", s.est_hours - part, "time"
                rest.scope_note = "The rest of this step, for when you have more time after your target date."
                optional.append(rest)
                s.shortened_from, s.est_hours, s.title = s.est_hours, part, f"{s.title} (part 1)"
                s.deliverable = f"Part 1 of: {s.deliverable}"
                s.done_when = f"About {part} hours in, with your progress saved toward the full check: {s.done_when}"
                s.scope_note = (f"Shortened to fit your time: about {part} of {s.shortened_from} hours now. "
                                f"Part 2 ({rest.est_hours} hours) is in your optional items.")
            left -= s.est_hours
            timeline.append(s)

    # IDs, dates, costs (first buyer pays), and suggestions
    start, hpw, used, bought = start_date(gap_list, today), ctx.hours_per_week, 0, set()
    for n, s in enumerate(timeline, 1):
        s.step_id = f"S{n}"
        s.phase, s.start_date, s.end_date = _phase(used, hpw), _on_day(start, used, hpw), _on_day(start, used + s.est_hours, hpw)
        used += s.est_hours
        s.cost_usd = 0 if s.title.endswith("(part 2)") else cost(set(s.resource_ids) - bought)
        bought |= set(s.resource_ids)
    for n, s in enumerate(optional, 1):
        s.step_id, s.phase, s.start_date, s.end_date = f"O{n}", "days_90_plus", None, None
        s.cost_usd = 0 if s.title.endswith("(part 2)") else cost(set(s.resource_ids) - bought)
    for d in deferred:
        item = next((s for s in optional if d.gap_id in s.gap_ids), None)
        if item:
            d.reason += f" It's listed as optional item {item.step_id}."
    budget_left = None if budget is None else budget - cost(bought)
    for s in [*timeline, *optional]:
        s.suggestions = _suggestions(s, gap_by_id[s.gap_ids[0]], role, budget_left)

    n_high = sum(1 for g in gap_list.gaps if g.severity == "high")
    summary = (f"Your {role.title} roadmap: {len(timeline)} steps, most important first"
               f" ({n_high} high priority), about {used} hours total.")
    if any(s.shortened_from for s in timeline):
        summary += " Big priorities were shortened to fit your time rather than dropped."
    if optional:
        summary += f" {len(optional)} optional item(s) are kept aside in case you get more time or budget."
    return RoadmapDraft(summary=summary, steps=timeline, deferred=deferred, optional=optional)
