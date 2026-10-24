"""Checks run in code on every roadmap, AI-written or not.

check() returns (errors, warnings). The planner's output must pass with no
errors (the tests enforce that), and so must the plan after tips are added.
"""
import re
from datetime import date
from typing import Optional

from . import catalog
from .schemas import GapList, RoadmapDraft

BANNED_PHRASES = [
    "network more", "improve your skills", "gain experience", "get experience",
    "learn more about", "brush up on", "familiarize yourself", "keep learning",
    "stay up to date", "build your skills", "work on your", "consider learning",
    "practice more", "as needed", "various resources", "online resources",
]
URL_RE = re.compile(r"https?://|www\.", re.I)
MIN_TEXT = 15         # deliverable / done_when shorter than this can't be concrete
HOURS_SLACK = 1.10     # allow 10% over the available hours


def start_date(gap_list: GapList, today: Optional[date] = None) -> date:
    return gap_list.user_context.start_date or today or date.today()


def available_hours(gap_list: GapList, today: Optional[date] = None) -> int:
    days = (gap_list.user_context.target_date - start_date(gap_list, today)).days
    weeks = max(days, 7) / 7
    return int(gap_list.user_context.hours_per_week * weeks)


def _find_cycle(deps: dict[str, list[str]]) -> Optional[str]:
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(node: str) -> Optional[str]:
        if state.get(node) == 1:
            return node
        if state.get(node) == 2:
            return None
        state[node] = 1
        for nxt in deps.get(node, []):
            if (hit := visit(nxt)):
                return hit
        state[node] = 2
        return None

    for node in deps:
        if (hit := visit(node)):
            return hit
    return None


def check(draft: RoadmapDraft, gap_list: GapList,
          today: Optional[date] = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    gaps = {g.gap_id: g for g in gap_list.gaps}
    resources = catalog.resources()
    projects = catalog.projects()
    step_ids = [s.step_id for s in draft.steps]
    all_ids = step_ids + [s.step_id for s in draft.optional]

    if len(set(all_ids)) != len(all_ids):
        errors.append("Duplicate step_id values.")

    covered: set[str] = set()
    # Optional items are shown to users too, so they get the same checks; only plan steps cover gaps.
    for s, in_plan in [*((s, True) for s in draft.steps), *((s, False) for s in draft.optional)]:
        if not s.gap_ids:
            errors.append(f"{s.step_id}: cites no gap_id.")
        for gid in s.gap_ids:
            if gid in gaps:
                if in_plan:
                    covered.add(gid)
            else:
                errors.append(f"{s.step_id}: unknown gap_id '{gid}'.")
        for rid in [*s.resource_ids, *(x.resource_id for x in s.suggestions)]:
            if rid not in resources:
                errors.append(f"{s.step_id}: resource_id '{rid}' is not in the catalog.")
        if s.project_id and s.project_id not in projects:
            errors.append(f"{s.step_id}: project_id '{s.project_id}' is not a known template.")
        for dep in s.depends_on:
            if dep not in step_ids:
                errors.append(f"{s.step_id}: depends_on unknown step '{dep}'.")
        if len(s.deliverable.strip()) < MIN_TEXT:
            errors.append(f"{s.step_id}: deliverable is missing or too vague.")
        if len(s.done_when.strip()) < MIN_TEXT:
            errors.append(f"{s.step_id}: done_when is missing or too vague.")
        if s.est_hours <= 0:
            errors.append(f"{s.step_id}: est_hours must be positive.")
        text = " ".join([s.title, s.why, s.deliverable, s.done_when, s.tip or "", s.scope_note or "",
                         *(x.reason for x in s.suggestions)]).lower()
        if URL_RE.search(text):
            errors.append(f"{s.step_id}: contains a URL; links must come from the catalog.")
        for phrase in BANNED_PHRASES:
            if re.search(r"\b" + re.escape(phrase) + r"\b", text):
                errors.append(f"{s.step_id}: vague phrase '{phrase}'.")

    deferred = set()
    for d in draft.deferred:
        if d.gap_id not in gaps:
            errors.append(f"Deferred unknown gap_id '{d.gap_id}'.")
        elif not d.reason.strip():
            errors.append(f"Deferred gap '{d.gap_id}' has no reason.")
        deferred.add(d.gap_id)

    for gid, g in gaps.items():
        if g.peer_share == 0:
            continue  # no hire has it, so it's deliberately left out
        if gid not in covered and gid not in deferred:
            errors.append(f"Gap '{gid}' ({g.severity}) is neither covered nor deferred.")

    if (cycle := _find_cycle({s.step_id: s.depends_on for s in draft.steps})):
        errors.append(f"depends_on has a loop through '{cycle}'.")

    total = sum(s.est_hours for s in draft.steps)
    avail = available_hours(gap_list, today)
    if total > avail * HOURS_SLACK:
        errors.append(f"Plan needs {total} hours but only {avail} are available before the target date.")

    cost = sum(resources[r]["cost_usd"] for r in {r for s in draft.steps for r in s.resource_ids}
               if r in resources)
    budget = gap_list.user_context.budget_usd
    if budget is not None and cost > budget:
        warnings.append(f"Cited resources cost about ${cost}, over the ${budget} budget.")

    return errors, warnings
