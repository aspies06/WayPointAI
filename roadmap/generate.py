"""Entry point: generate_roadmap(gap_list) -> Roadmap.

The plan always comes from planner.py (catalog + rules), so it is grounded and
never empty. The local model then adds personal tips if it can:
  1. Demo mode (ROADMAP_DEMO=1): pre-saved roadmap for this gap list, instant.
  2. Cache: a personalized roadmap already made today for this exact gap list
     (phases and hours depend on the date, so older entries are not reused).
     Private by default: kept in memory only, for at most CACHE_TTL_S.
  3. Local model: tips + summary, each line checked. Label "Personalized roadmap".
  4. If the model is off, busy, slow, fails, or every line is rejected: the
     plan without tips. Label "Basic roadmap".
Raises AvailabilityNeeded if the user hasn't said how much time they have
(ask intake.QUESTIONS first), and ValidationError for invalid input.
Everything after that returns a Roadmap.
"""
import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import date
from pathlib import Path
from typing import Optional

from . import catalog, guardrails, local_model, personalize
from .intake import AvailabilityNeeded
from .planner import build_plan
from .schemas import FOCUS_LEVELS, ROLES, GapList, ResourceLink, Roadmap, RoadmapDraft

log = logging.getLogger("roadmap")

ROOT = Path(__file__).resolve().parent.parent
# Privacy: roadmaps can hold personal details (tips are written from the user's background), so
# by default they're cached in memory only and forgotten after a day. A disk cache is used only if
# ROADMAP_CACHE_DIR is set on purpose; its files are owner-only and deleted once they expire.
CACHE_DIR = Path(os.environ["ROADMAP_CACHE_DIR"]) if os.getenv("ROADMAP_CACHE_DIR") else None
CACHE_TTL_S = 24 * 3600
CACHE_MAX = 256  # roadmaps kept in memory
_memory: "OrderedDict[str, tuple[float, Roadmap]]" = OrderedDict()
_memory_lock = threading.Lock()
DEMO_DIR = ROOT / "demo"
LABELS = {"ai": "Personalized roadmap", "cache": "Personalized roadmap",
          "demo": "Personalized roadmap", "basic": "Basic roadmap"}


def cache_key(gap_list: GapList) -> str:
    canon = json.dumps(gap_list.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()  # full hash: two users must never share a key


def _load(directory: Path, key: str) -> Optional[Roadmap]:
    path = directory / f"{key}.json"
    try:
        return Roadmap.model_validate_json(path.read_text())
    except FileNotFoundError:
        return None
    except Exception as e:  # corrupt file: ignore it, don't crash the demo
        log.warning("ignoring unreadable %s: %s", path.name, type(e).__name__)  # never log its contents
        return None


def _save(directory: Path, key: str, roadmap: Roadmap) -> None:
    try:
        directory.mkdir(mode=0o700, exist_ok=True)
        path = directory / f"{key}.json"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # owner-only from the start
        with os.fdopen(fd, "w") as f:
            f.write(roadmap.model_dump_json(indent=2))
    except OSError as e:
        log.warning("could not write %s: %s", directory, e)


def _purge_expired(directory: Path) -> None:
    cutoff = time.time() - CACHE_TTL_S
    for path in directory.glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def _cache_get(key: str) -> Optional[Roadmap]:
    with _memory_lock:
        hit = _memory.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL_S:
            _memory.move_to_end(key)
            return hit[1].model_copy(deep=True)
        _memory.pop(key, None)
    if CACHE_DIR:
        path = CACHE_DIR / f"{key}.json"
        if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL_S:
            return _load(CACHE_DIR, key)
    return None


def _cache_put(key: str, roadmap: Roadmap) -> None:
    with _memory_lock:
        _memory[key] = (time.time(), roadmap.model_copy(deep=True))
        _memory.move_to_end(key)
        while len(_memory) > CACHE_MAX:
            _memory.popitem(last=False)
    if CACHE_DIR:
        _save(CACHE_DIR, key, roadmap)
        _purge_expired(CACHE_DIR)


def clear_cache() -> None:
    """Forget every cached roadmap (memory and, if configured, disk)."""
    with _memory_lock:
        _memory.clear()
    if CACHE_DIR:
        for path in CACHE_DIR.glob("*.json"):
            path.unlink(missing_ok=True)


def _finish(draft: RoadmapDraft, gap_list: GapList, source: str, today: Optional[date]) -> Roadmap:
    _, warnings = guardrails.check(draft, gap_list, today)
    if gap_list.target_role.role is None:
        warnings.append(f"'{gap_list.target_role.title}' isn't one of the roles this app is built for "
                        f"({', '.join(ROLES)}), so more gaps may be deferred.")
    if gap_list.target_role.level not in FOCUS_LEVELS:
        warnings.append("This app is built for internship, junior and mid-level roles; "
                        "this senior roadmap uses mid-level resources.")
    start = guardrails.start_date(gap_list, today)
    roadmap = Roadmap(
        **draft.model_dump(), target_role=gap_list.target_role, source=source,
        label=LABELS[source], total_hours=sum(s.est_hours for s in draft.steps),
        available_hours=guardrails.available_hours(gap_list, today),
        hours_per_week=gap_list.user_context.hours_per_week, start_date=start,
        finish_date=max((s.end_date for s in draft.steps if s.end_date), default=start),
        target_date=gap_list.user_context.target_date, warnings=warnings)
    res = catalog.resources()
    link = lambda r: ResourceLink(**{k: res[r][k] for k in ResourceLink.model_fields})
    for s in [*roadmap.steps, *roadmap.optional]:
        s.resources = [link(r) for r in s.resource_ids if r in res]
        for x in s.suggestions:
            x.resource = link(x.resource_id) if x.resource_id in res else None
    return roadmap


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
    if gap_list.user_context is None:
        raise AvailabilityNeeded()  # never guess someone's time; ask intake.QUESTIONS
    key = cache_key(gap_list)
    cache_file = f"{key}-{(today or date.today()).isoformat()}"

    if os.getenv("ROADMAP_DEMO") == "1" and (saved := _load(DEMO_DIR, key)):
        saved.source = "demo"
        return saved
    if use_cache and (cached := _cache_get(cache_file)):
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
            _cache_put(cache_file, roadmap)
            return roadmap

    return _finish(plan, gap_list, "basic", today)
