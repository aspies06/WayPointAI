"""Live scoreboard: runs every persona through the local model and scores the tips.

    python scripts/run_eval.py                      # every persona, once
    python scripts/run_eval.py --only swe_intern    # one persona
    python scripts/run_eval.py --level internship   # every persona at one level
    python scripts/run_eval.py --role "QA Engineer" # every persona for one role

Downloads the model on first run (needs torch + transformers). The plan itself
is deterministic, so only the model's tips and summary vary between runs.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roadmap import GapList, local_model, personalize  # noqa: E402
from roadmap.guardrails import check  # noqa: E402
from roadmap.planner import build_plan  # noqa: E402
from roadmap.schemas import ROLES  # noqa: E402

PERSONAS = Path(__file__).resolve().parent.parent / "tests" / "personas"
OUT = Path(__file__).resolve().parent.parent / "eval_results"


def score(name: str, gl: GapList, runs: int) -> dict:
    plan = build_plan(gl)
    row = {"persona": name, "role": gl.target_role.role or "-", "level": gl.target_role.level,
           "runs": runs, "steps": len(plan.steps), "ok": 0, "tips": [], "summary": 0, "pass": 0, "secs": [], "rejected": [], "errors": []}
    if not plan.steps:
        return row
    ids = {s.step_id for s in plan.steps}
    for _ in range(runs):
        t = time.time()
        try:
            output = local_model.generate_with_timeout(local_model.hf_generate,
                                                       personalize.messages_for(gl, plan))
        except Exception as e:
            row["secs"].append(time.time() - t)
            row["errors"].append(f"call failed: {type(e).__name__}: {e}"[:200])
            continue
        row["secs"].append(time.time() - t)
        row["ok"] += 1
        tips, summary, rejected = personalize.parse(output, ids)
        row["tips"].append(len(tips) / len(ids))
        row["summary"] += summary is not None
        row["rejected"] += rejected
        errors, _ = check(personalize.apply(plan, tips, summary), gl)
        row["pass"] += not errors
        row["errors"] += errors
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--only")
    ap.add_argument("--level", choices=["internship", "entry", "mid"])
    ap.add_argument("--role", choices=ROLES)
    args = ap.parse_args()

    rows = []
    for path in sorted(PERSONAS.glob("*.json")):
        if args.only and path.stem != args.only:
            continue
        gl = GapList.model_validate_json(path.read_text())
        if args.level and gl.target_role.level != args.level:
            continue
        if args.role and gl.target_role.role != args.role:
            continue
        rows.append(score(path.stem, gl, args.runs))

    print(f"\nmodel: {local_model.MODEL_ID}\n")
    print(f"{'persona':26} {'role':22} {'level':10} {'steps':>5} {'valid':>6} {'tips':>5} {'summ':>5} {'guard':>6} {'avg s':>6}")
    for r in rows:
        tips = sum(r["tips"]) / len(r["tips"]) if r["tips"] else 0
        secs = r["secs"] or [0]
        print(f"{r['persona']:26} {r['role']:22} {r['level']:10} {r['steps']:>5} {r['ok']:>3}/{r['runs']:<2} {tips:>5.0%} "
              f"{r['summary']:>5} {r['pass']:>3}/{r['runs']:<2} {sum(secs)/len(secs):>6.1f}")
    for r in rows:
        for e in r["rejected"] + r["errors"]:
            print(f"  [{r['persona']}] {e}")

    OUT.mkdir(exist_ok=True)
    out = OUT / f"eval_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
