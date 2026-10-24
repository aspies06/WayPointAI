"""Walk through how one gap list becomes a roadmap, decision by decision.

    python scripts/explain.py tests/personas/data_scientist_intern.json

Read-only and offline: it calls the same functions generate_roadmap() uses,
but prints what each stage saw and chose. The local model is not run.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roadmap import GapList, catalog, guardrails  # noqa: E402
from roadmap.planner import SEV_ORDER, build_plan  # noqa: E402

if len(sys.argv) != 2:
    sys.exit("usage: python scripts/explain.py path/to/gap_list.json")

raw = json.loads(Path(sys.argv[1]).read_text())
gl = GapList.model_validate(raw)
if gl.user_context is None:
    sys.exit("This gap list has no user_context yet; run python -m roadmap on it to answer the questions.")
role, ctx = gl.target_role, gl.user_context


def head(n, text):
    print(f"\n{'=' * 70}\n {n}. {text}\n{'=' * 70}")


head(1, "Read and clean up the input")
print(f"  title  : {role.title}")
print(f"  level  : {raw['target_role'].get('level', 'entry')!r} -> {role.level!r}")
print(f"  role   : {raw['target_role'].get('role')!r} -> {role.role!r}"
      + ("  (inferred from title)" if not raw["target_role"].get("role") else ""))
avail = guardrails.available_hours(gl)
print(f"  time   : {ctx.hours_per_week} h/week until {ctx.target_date} = {avail} hours available")
print(f"  budget : {'no limit' if ctx.budget_usd is None else '$' + str(ctx.budget_usd)}")

head(2, "Order the gaps: high severity first, then most common among hires")
gaps = sorted(gl.gaps, key=lambda g: (SEV_ORDER[g.severity], -g.peer_share))
for g in gaps:
    print(f"  {g.gap_id:4} {g.severity:6} {g.peer_share:3}%  {g.item}")

head(3, "Match each gap to the catalog")
for g in gaps:
    print(f"\n  {g.gap_id}: \"{g.item}\" ({g.category})")
    projs = catalog.projects_for(g.item, role.level, role.role)
    skipped = [p for p in catalog.projects_for(g.item) if p not in projs]
    res = catalog.resources_for(g.item, role.level, role.role)
    for p in projs[:3]:
        print(f"    project  {p['id']:26} {p['est_hours']:>3}h  {p['title']}")
    for p in skipped[:3]:
        why = "level" if not catalog._suits(p, role.level) else "role"
        print(f"    skipped  {p['id']:26} wrong {why} (suits {p.get('levels') if why == 'level' else p.get('roles')})")
    for r in res[:3]:
        print(f"    resource {r['id']:26} {r['level']:10} ${r['cost_usd']:<4} {r['name']}")
    if not (projs or res):
        print("    nothing in the catalog matches")

head(4, "Build the plan: budget first, then time by priority (big priorities shortened, not dropped)")
plan = build_plan(gl)
used = 0
for s in plan.steps:
    used += s.est_hours
    short = f" (cut from {s.shortened_from}h)" if s.shortened_from else ""
    print(f"  {s.step_id:3} {s.priority:12} +{s.est_hours:>3}h{short} (total {used:>3}/{avail}) "
          f"${s.cost_usd:<4} [{s.benefit}]  {s.title}")
    for x in s.suggestions:
        print(f"        worth considering ({x.kind}): {x.reason}")
for s in plan.optional:
    print(f"  {s.step_id:3} optional       (doesn't fit {s.optional_because}, ${s.cost_usd}, {s.est_hours}h)  {s.gap_ids}  {s.title}")
for d in plan.deferred:
    print(f"  deferred {d.gap_id}: {d.reason}")

head(5, "Guardrails")
errors, warnings = guardrails.check(plan, gl)
print("  errors  :", errors or "none")
print("  warnings:", warnings or "none")

head(6, "Personal tips (not run here)")
print("  generate_roadmap() would now ask the local model for one tip per step,")
print("  keep only tips that pass the checks in personalize.py, and label the result")
print("  'Personalized roadmap'. With the model off or busy you get 'Basic roadmap'.")
print(f"\n  Summary: {plan.summary}\n")
