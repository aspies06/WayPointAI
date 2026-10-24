"""What people in each role do, from O*NET.

Reads data/role_insights.json, built by scripts/build_role_insights.py from O*NET 31.0
(U.S. Department of Labor, CC BY 4.0): the tasks rated most important by people who hold
the closest occupation, and the technologies O*NET flags as In Demand (often listed in
employer job postings for that occupation). No scraped job-board data is used.
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

DATA = Path(__file__).resolve().parent / "data" / "role_insights.json"
QUALIFIERS = {"CI"}
VENDORS = ("The MathWorks", "Microsoft", "Apple", "Atlassian", "Amazon", "Google", "IBM", "Oracle", "Adobe", "Apache")


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def roles() -> list[str]:
    return list(_data()["roles"])


def match_terms(name: str) -> list[str]:
    """Names people actually write for an O*NET technology: "Microsoft Active Directory" ->
    "Active Directory", "Structured query language SQL" -> "SQL", "Amazon Web Services AWS
    software" -> "AWS". The full name is always included."""
    terms = [name]
    base = re.sub(r"\s+software$", "", name)
    words = base.split()
    if len(words) > 1 and re.fullmatch(r"[A-Z][A-Z0-9]{2,}", words[-1]):
        # Trailing acronym: "Amazon Web Services AWS" -> "AWS" and "Amazon Web Services".
        # The vendor stays in the long form, so "Web Services" alone never matches.
        terms += [words[-1], " ".join(words[:-1])]
    else:
        if len(words) > 1 and words[-1] in QUALIFIERS:  # "Jenkins CI" -> "Jenkins"; "Power BI" stays
            base = " ".join(words[:-1])
        for vendor in VENDORS:
            if base.startswith(vendor + " "):
                base = base[len(vendor) + 1:]
                break
        terms.append(base)
    seen, out = set(), []
    for term in terms:
        if term and term.casefold() not in seen:
            seen.add(term.casefold())
            out.append(term)
    return out


def for_role(role: str, n_tasks: int = 6) -> Optional[dict]:
    """Insights for one role, or None for an unknown role."""
    data = _data()
    entry = data["roles"].get(role)
    if entry is None:
        return None
    onet = entry["onet"]
    return {
        "role": role,
        "people_in_role": {
            "occupation": onet["title"],
            "onet_code": onet["code"],
            "match": onet["match"],
            "tasks": [t["task"] for t in onet["tasks"][:n_tasks]],
        },
        # O*NET's own employer-demand signal for the occupation; "Hot" is across all jobs, so it's left out.
        "in_demand_technologies": [{"name": t["name"], "terms": match_terms(t["name"])}
                                   for t in onet["technologies"] if t["in_demand"]],
        "sources": [data["sources"]["onet"]["attribution"]],
    }
