"""Entry point: generate_roadmap(gap_list) -> Roadmap.

The plan always comes from planner.py (catalog + rules), so it is grounded and
never empty. The local model then adds personal tips if it can:
  1. Demo mode (ROADMAP_DEMO=1): pre-saved roadmap for this gap list, instant.
  2. Cache: a personalized roadmap already made today for this exact gap list
     (phases and hours depend on the date, so older entries are not reused).
  3. Local model: tips + summary, each line checked. Label "Personalized roadmap".
  4. If the model is off, busy, slow, fails, or every line is rejected: the
     plan without tips. Label "Basic roadmap".
Only invalid input raises. Everything after that returns a Roadmap.
"""
import hashlib
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional

from . import guardrails, local_model, personalize
from .planner import build_plan
from .schemas import FOCUS_LEVELS, ROLES, GapList, Roadmap, RoadmapDraft

log = logging.getLogger("roadmap")

ROOT = Path(__file__).resolve().parent.parent
# Holds users' gap lists (backgrounds included); point it at private storage in production.
CACHE_DIR = Path(os.getenv("ROADMAP_CACHE_DIR", ROOT / "cache"))
DEMO_DIR = ROOT / "demo"
LABELS = {"ai": "Personalized roadmap", "cache": "Personalized roadmap",
          "demo": "Personalized roadmap", "basic": "Basic roadmap"}


def cache_key(gap_list: GapList) -> str:
    canon = json.dumps(gap_list.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def _load(directory: Path, key: str) -> Optional[Roadmap]:
    path = directory / f"{key}.json"
    try:
        return Roadmap.model_validate_json(path.read_text())
    except FileNotFoundError:
        return None
    except Exception as e:  # corrupt file: ignore it, don't crash the demo
        log.warning("ignoring unreadable %s: %s", path, e)
        return None


def _save(directory: Path, key: str, roadmap: Roadmap) -> None:
    try:
        directory.mkdir(exist_ok=True)
        (directory / f"{key}.json").write_text(roadmap.model_dump_json(indent=2))
    except OSError as e:
        log.warning("could not write %s: %s", directory, e)


def _finish(draft: RoadmapDraft, gap_list: GapList, source: str, today: Optional[date]) -> Roadmap:
    _, warnings = guardrails.check(draft, gap_list, today)
    if gap_list.target_role.role is None:
        warnings.append(f"'{gap_list.target_role.title}' isn't one of the roles this app is built for "
                        f"({', '.join(ROLES)}), so more gaps may be deferred.")
    if gap_list.target_role.level not in FOCUS_LEVELS:
        warnings.append("This app is built for internship, junior and mid-level roles; "
                        "this senior roadmap uses mid-level resources.")
    return Roadmap(
        **draft.model_dump(), target_role=gap_list.target_role, source=source,
        label=LABELS[source], total_hours=sum(s.est_hours for s in draft.steps),
        available_hours=guardrails.available_hours(gap_list, today), warnings=warnings)


def personalize_plan(gap_list: GapList, plan: RoadmapDraft,
                     model: local_model.TextModel) -> Optional[RoadmapDraft]:
    """Returns the plan with tips, or None if the model gave nothing usable."""
    try:
        output = local_model.generate_with_timeout(model, personalize.messages_for(gap_list, plan))
    except Exception as e:  # timeout, download failure, out of memory, ...
        log.warning("local model failed: %s: %s", type(e).__name__, e)
        return None
    tips, summary, rejected = personalize.parse(output, {s.step_id for s in plan.steps})
    if rejected:
        log.info("rejected model lines: %s", rejected)
    if not tips:
        log.warning("local model gave no usable tips")
        return None
    return personalize.apply(plan, tips, summary)


def generate_roadmap(gap_list: GapList | dict, today: Optional[date] = None,
                     use_cache: bool = True,
                     model: Optional[local_model.TextModel] = None) -> Roadmap:
    if not isinstance(gap_list, GapList):
        gap_list = GapList.model_validate(gap_list)  # bad input is the caller's bug: let it raise
    key = cache_key(gap_list)
    cache_file = f"{key}-{(today or date.today()).isoformat()}"

    if os.getenv("ROADMAP_DEMO") == "1" and (saved := _load(DEMO_DIR, key)):
        saved.source = "demo"
        return saved
    if use_cache and (cached := _load(CACHE_DIR, cache_file)):
        cached.source = "cache"
        return cached

    plan = build_plan(gap_list, today)
    errors, _ = guardrails.check(plan, gap_list, today)
    if errors:  # a planner bug, not a user problem: log it loudly but still show the plan
        log.error("planner output failed guardrails: %s", errors)

    use_model = os.getenv("ROADMAP_AI", "1") != "0" and os.getenv("ROADMAP_DEMO") != "1"
    if plan.steps and use_model:
        personal = personalize_plan(gap_list, plan, model or local_model.hf_generate)
        if personal and not guardrails.check(personal, gap_list, today)[0]:
            roadmap = _finish(personal, gap_list, "ai", today)
            _save(CACHE_DIR, cache_file, roadmap)
            return roadmap

    return _finish(plan, gap_list, "basic", today)
