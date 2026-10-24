"""
skills/role_profiles.py
-----------------------
Role profiles for the 9 tech roles supported by WayPointAI, built from O*NET 31.0
(U.S. Department of Labor, Employment and Training Administration; CC BY 4.0).

Each profile comes from the closest O*NET occupation (see data/role_insights.json, built by
scripts/build_role_insights.py). Nothing here is hand-estimated:

- required_skills: technologies O*NET flags as In Demand for the occupation (often listed
  in employer job postings), named the way resumes name them ("AWS", "SQL").
- preferred_skills: transferable skills rated 3.75 or higher in importance (1-5) by people
  who hold the job, e.g. Programming.
- avg_years_experience: the median related work experience workers report (lower bound of
  the median O*NET category). O*NET covers workers at all career stages, so this is only
  applied to mid-level and senior targets (see skills/career_pipeline.py).
- common_education: education levels at least 20% of workers report the job requires.

O*NET measures importance and demand, not the share of hires who have a skill, so each skill
records its `basis` and the roadmap words it accordingly. `frequency` only orders skills:
in-demand technologies that are also Hot 0.7, other in-demand technologies 0.5, rated skills
(importance - 1) / 4 (O*NET's standard 0-100 conversion, as a fraction).

Usage
-----
    from skills.role_profiles import ROLE_PROFILES

    profile = ROLE_PROFILES["Software Engineer"]
    # pass to gap_analyzer.analyze_gap(resume, profile)
"""

from __future__ import annotations

from skills.role_insights import _data, match_terms

MIN_IMPORTANCE = 3.75
MIN_EDUCATION_SHARE = 0.2
# Lower bound in years of each O*NET Related Work Experience category.
EXPERIENCE_YEARS = {1: 0, 2: 0, 3: 1 / 12, 4: 0.25, 5: 0.5, 6: 1, 7: 2, 8: 4, 9: 6, 10: 8, 11: 10}
KEEP_VENDOR = {"Office", "Project", "Teams"}  # too generic without "Microsoft"


def display_name(name: str) -> str:
    """The name a resume would use: "Structured query language SQL" -> "SQL",
    "Microsoft Active Directory" -> "Active Directory"."""
    terms = match_terms(name)
    if len(terms) == 1:
        return name
    short = terms[1]
    return name.removesuffix(" software") if short in KEEP_VENDOR else short


def _median_experience(categories: list[dict]) -> float:
    total = 0.0
    for category in sorted(categories, key=lambda c: c["category"]):
        total += category["share"]
        if total >= 0.5:
            return float(EXPERIENCE_YEARS[category["category"]])
    return 0.0


def _profile(role: str, onet: dict) -> dict:
    required = [{
        "skill": display_name(t["name"]),
        "frequency": 0.7 if t["hot"] else 0.5,
        "basis": "in_demand",
        "aliases": match_terms(t["name"]),
    } for t in onet["technologies"] if t["in_demand"]]
    preferred = [{
        "skill": s["name"],
        "frequency": round((s["importance"] - 1) / 4, 3),
        "basis": "importance",
        "importance": s["importance"],
    } for s in onet["skills"] if s["importance"] >= MIN_IMPORTANCE]
    return {
        "role": role,
        "onet_occupation": onet["title"],
        "onet_code": onet["code"],
        "required_skills": required,
        "preferred_skills": preferred,
        "avg_years_experience": _median_experience(onet["experience"]),
        "common_education": [e["level"] for e in onet["education"] if e["share"] >= MIN_EDUCATION_SHARE],
    }


ROLE_PROFILES: dict[str, dict] = {role: _profile(role, entry["onet"]) for role, entry in _data()["roles"].items()}
