"""Loads the resource catalog and project templates, and matches them to gaps."""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LEVELS = ["internship", "entry", "mid", "senior"]


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9+#&/.-]+", " ", text.lower()).replace(". ", " ").strip(" .") + " "


@lru_cache
def resources() -> dict[str, dict]:
    data = json.loads((DATA_DIR / "catalog.json").read_text())
    return {r["id"]: r for r in data["resources"]}


@lru_cache
def projects() -> dict[str, dict]:
    data = json.loads((DATA_DIR / "projects.json").read_text())
    return {p["id"]: p for p in data["projects"]}


def _specificity(entry: dict, gap_item: str) -> int:
    """Length of the longest alias found in the gap text; 0 means no match."""
    item = _norm(gap_item)
    return max((len(a) for a in entry["matches"] if _norm(a) in item), default=0)


def _fits_role(entry: dict, role: Optional[str]) -> bool:
    """Entries list the roles they serve; no list (or no known role) means any role."""
    return role is None or "roles" not in entry or role in entry["roles"]


def resources_for(gap_item: str, level: Optional[str] = None, role: Optional[str] = None) -> list[dict]:
    """Matching resources, best first: built for the role, most specific alias, closest level,
    cheapest, shortest. Off-role resources still match, so shared skills like Docker work for everyone."""
    want = LEVELS.index(level) if level in LEVELS else 1
    scored = [(s, r) for r in resources().values() if (s := _specificity(r, gap_item))]
    scored.sort(key=lambda sr: (not _fits_role(sr[1], role), -sr[0],
                                abs(LEVELS.index(sr[1]["level"]) - want), sr[1]["cost_usd"], sr[1]["hours"]))
    return [r for _, r in scored]


def _hits(entry: dict, gap_item: str) -> int:
    item = _norm(gap_item)
    return sum(_norm(a) in item for a in entry["matches"])


def _suits(project: dict, level: Optional[str]) -> bool:
    """Templates list the levels they fit; senior uses the mid ones."""
    if level is None or "levels" not in project:
        return True
    return ("mid" if level == "senior" else level) in project["levels"]


def projects_for(gap_item: str, level: Optional[str] = None, role: Optional[str] = None) -> list[dict]:
    """Matching templates for this level and role, best first: most specific alias, then most aliases hit."""
    scored = [(s, p) for p in projects().values()
              if _suits(p, level) and _fits_role(p, role) and (s := _specificity(p, gap_item))]
    scored.sort(key=lambda sp: (-sp[0], -_hits(sp[1], gap_item)))
    return [p for _, p in scored]
