"""How the user's education compares with what people in a job report it requires (O*NET).

Advice only: education never becomes a gap, and no degree is assumed. The figures are O*NET's
Education, Training, and Experience survey: the share of workers in the closest occupation who
say each level is required for the job. Data Scientists has no figures in O*NET 31.0, so that
role says so instead of guessing.
"""
from typing import Optional

from skills.role_insights import _data

# The user's choices: value -> (how we say it, O*NET's 1-12 education scale)
CHOICES = {
    "high_school": ("a high school diploma or GED", 2),
    "some_college": ("some college or a certificate", 4),
    "in_progress": ("a degree in progress", None),
    "associate": ("an associate degree", 5),
    "bachelor": ("a bachelor's degree", 6),
    "master": ("a master's degree", 8),
    "doctoral": ("a doctoral degree", 11),
}
LABELS = {
    "high_school": "High school diploma or GED",
    "some_college": "Some college or a certificate",
    "in_progress": "Working on a degree",
    "associate": "Associate degree",
    "bachelor": "Bachelor's degree",
    "master": "Master's degree",
    "doctoral": "Doctoral degree (PhD)",
}
# O*NET's level names, in order (Required Level of Education, categories 1-12)
ONET_ORDER = [
    "Less than a High School Diploma", "High School Diploma", "Post-Secondary Certificate", "Some College Courses",
    "Associate's Degree", "Bachelor's Degree", "Post-Baccalaureate Certificate", "Master's Degree",
    "Post-Master's Certificate", "First Professional Degree", "Doctoral Degree", "Post-Doctoral Training",
]
SHORT = {"Associate's Degree": "an associate degree", "Bachelor's Degree": "a bachelor's degree",
         "Master's Degree": "a master's degree", "Doctoral Degree": "a doctoral degree",
         "High School Diploma": "a high school diploma", "Post-Secondary Certificate": "a post-secondary certificate",
         "Some College Courses": "some college", "Post-Baccalaureate Certificate": "a post-bachelor's certificate"}


def _rank(level_name: str) -> int:
    """O*NET's long names ("Associate's Degree or other 2-year degree") -> 1-12."""
    return next(i + 1 for i, name in enumerate(ONET_ORDER) if level_name.startswith(name))


def _short(level_name: str) -> str:
    return SHORT.get(ONET_ORDER[_rank(level_name) - 1], level_name.split(" - ")[0].lower())


def advice(role: str, education: str, field_of_study: str = "") -> Optional[dict]:
    """{"message", "meets"} for the roadmap, or None if the user didn't say."""
    if education not in CHOICES:
        return None
    onet = _data()["roles"][role]["onet"]
    levels = onet["education"]
    yours, your_rank = CHOICES[education]
    field = f" in {field_of_study.strip()}" if field_of_study.strip() else ""
    source = (f" (O*NET's closest job: {onet['title']})" if onet["match"] == "approximate" else "")
    if not levels:
        return {"message": f"O*NET has no education figures for this job, so we can't compare {yours}{field} "
                           "with it. Job listings for the roles you want are the best guide.", "meets": None}

    top = max(levels, key=lambda e: e["share"])
    top_rank = _rank(top["level"])
    common = (f"{_short(top['level']).capitalize()} is the most common requirement: {top['share']:.0%} of people "
              f"in this job report it{source}.")
    if your_rank is None:  # still studying
        return {"message": f"{common} You're working on a degree{field}; internships and projects while you study "
                           "are the usual way in.", "meets": None}
    no_more = sum(e["share"] for e in levels if _rank(e["level"]) <= your_rank)
    if your_rank >= top_rank:
        return {"message": f"You have {yours}{field}, which meets the most common requirement. {common}",
                "meets": True}
    return {"message": f"{common} You have {yours}{field}; {no_more:.0%} of people in this job report needing no more "
                       "than that. A degree isn't the only way in: skills, projects and certifications on this plan "
                       "count, though some employers do screen for a degree.", "meets": False}
