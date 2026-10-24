"""
gap_analyzer.py
---------------
Pure matching and gap-analysis logic for WayPointAI (Component 3, Person A).

Inputs
------
role_profile : dict  — schema produced by Component 1 (data engineering)
resume       : dict  — schema produced by Component 2 (resume parsing)

Output
------
GapResult dict — consumed by Component 4 (LLM/roadmap) and Component 5
                 (frontend) via the FastAPI layer owned by Person B.

All functions are deterministic and have no framework dependencies.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Synonym map
# Keys are non-canonical forms; values are the canonical skill name.
# Extend this once Component 1 delivers the full vocabulary.
# ---------------------------------------------------------------------------
SKILL_SYNONYMS: dict[str, str] = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "js": "javascript",
    "ts": "typescript",
    "node": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "cv": "computer vision",
    "nlp": "natural language processing",
    "dl": "deep learning",
    "tf": "tensorflow",
    "scikit": "scikit-learn",
    "sklearn": "scikit-learn",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    "r lang": "r",
}


def normalize_skill(skill: str) -> str:
    """Return the canonical, lowercased form of a skill string.

    Strips surrounding whitespace, lowercases, then applies the synonym map
    so that variant spellings resolve to a single canonical token.

    Examples
    --------
    >>> normalize_skill("  ML ")
    'machine learning'
    >>> normalize_skill("Python")
    'python'
    """
    normalized = skill.strip().lower()
    return SKILL_SYNONYMS.get(normalized, normalized)


def match_skills(
    resume_skills: list[str],
    role_skills: list[dict],
) -> tuple[list[str], list[dict]]:
    """Split role skills into those present in and missing from the resume.

    Parameters
    ----------
    resume_skills:
        Raw skill strings extracted from the resume (Component 2 output).
    role_skills:
        List of ``{"skill": str, "frequency": float}`` dicts from the role
        profile (Component 1 output).  May be ``required_skills`` or
        ``preferred_skills`` — the caller decides which list to pass.

    Returns
    -------
    present : list[str]
        Canonical skill names found in both the resume and the role profile.
    missing : list[dict]
        Role-skill dicts (``{"skill", "frequency"}``) not covered by the
        resume, preserving the original frequency values.
    """
    resume_set = {normalize_skill(s) for s in resume_skills}

    present: list[str] = []
    missing: list[dict] = []

    for entry in role_skills:
        canonical = normalize_skill(entry["skill"])
        if canonical in resume_set:
            present.append(canonical)
        else:
            missing.append({"skill": entry["skill"], "frequency": entry["frequency"]})

    return present, missing


def rank_missing_skills(missing: list[dict]) -> list[dict]:
    """Sort missing skills by posting frequency (descending) and add priority.

    Parameters
    ----------
    missing:
        Output of :func:`match_skills` — list of
        ``{"skill": str, "frequency": float}`` dicts.

    Returns
    -------
    List of ``{"skill": str, "priority": int, "frequency": float}`` dicts
    where ``priority`` 1 is the most in-demand gap.
    """
    sorted_skills = sorted(missing, key=lambda x: x["frequency"], reverse=True)
    return [
        {"skill": entry["skill"], "priority": i + 1, "frequency": entry["frequency"]}
        for i, entry in enumerate(sorted_skills)
    ]


def compute_score(present: list[str], role_skills: list[dict]) -> int:
    """Return a 0–100 match score weighted by posting frequency.

    Score = sum(frequency of matched skills) / sum(frequency of all role
    skills) * 100, rounded to the nearest integer.

    A role profile with no skills returns 0.
    """
    total_weight = sum(entry["frequency"] for entry in role_skills)
    if total_weight == 0:
        return 0

    canonical_role = {normalize_skill(e["skill"]): e["frequency"] for e in role_skills}
    matched_weight = sum(canonical_role.get(s, 0.0) for s in present)

    return round((matched_weight / total_weight) * 100)


def analyze_gap(resume: dict, role_profile: dict) -> dict:
    """Compute the full gap analysis between a resume and a role profile.

    Parameters
    ----------
    resume:
        Parsed resume object from Component 2::

            {
                "skills": ["Python", "Excel"],
                "education": [{"degree": "BSc", "field": "Economics"}],
                "experience_years": 1.5,
                "projects": ["Built a sales dashboard"]
            }

    role_profile:
        Role profile from Component 1::

            {
                "role": "Data Scientist",
                "required_skills": [{"skill": "Python", "frequency": 0.95}, ...],
                "preferred_skills": [{"skill": "Tableau", "frequency": 0.40}, ...],
                "avg_years_experience": 3.2,
                "common_education": ["Computer Science", "Statistics"]
            }

    Returns
    -------
    GapResult dict::

        {
            "match_score": 42,
            "skills_present": ["python"],
            "skills_missing": [
                {"skill": "SQL", "priority": 1, "frequency": 0.82},
                ...
            ],
            "experience_gap": 1.7,
            "weak_areas": ["SQL", "Machine Learning"]
        }

    ``weak_areas`` contains the top-3 missing required skills by frequency —
    concrete themes for the roadmap prompt.
    """
    resume_skills: list[str] = resume.get("skills", [])
    required: list[dict] = role_profile.get("required_skills", [])
    preferred: list[dict] = role_profile.get("preferred_skills", [])
    all_role_skills = required + preferred

    present, missing_raw = match_skills(resume_skills, all_role_skills)
    skills_missing = rank_missing_skills(missing_raw)

    score = compute_score(present, all_role_skills)

    experience_gap = round(
        max(0.0, role_profile.get("avg_years_experience", 0.0)
            - resume.get("experience_years", 0.0)),
        1,
    )

    # Weak areas: top-3 missing *required* skills by frequency
    _, missing_required_raw = match_skills(resume_skills, required)
    top_missing_required = rank_missing_skills(missing_required_raw)
    weak_areas = [entry["skill"] for entry in top_missing_required[:3]]

    return {
        "match_score": score,
        "skills_present": present,
        "skills_missing": skills_missing,
        "experience_gap": experience_gap,
        "weak_areas": weak_areas,
    }


# ---------------------------------------------------------------------------
# Severity thresholds (per gap_list_spec.md)
# ---------------------------------------------------------------------------
_HIGH_THRESHOLD = 60
_MEDIUM_THRESHOLD = 30


def _severity(peer_share: int) -> str:
    if peer_share >= _HIGH_THRESHOLD:
        return "high"
    if peer_share >= _MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def build_gap_list(
    gap_result: dict,
    target_role: dict,
    user_context: dict,
    resume: dict | None = None,
) -> dict:
    """Convert an ``analyze_gap`` result into the gap list schema expected by
    ``roadmap.generate_roadmap()``.

    Parameters
    ----------
    gap_result:
        The dict returned by :func:`analyze_gap`.
    target_role:
        ``{"title": str, "level": str, "role": str}`` — the role as shown to
        the user.  ``level`` must be one of ``internship``, ``entry``, ``mid``,
        ``senior`` (or an accepted alias).  ``role`` must be one of the 9
        supported roles.
    user_context:
        ``{"hours_per_week": int, "target_date": "YYYY-MM-DD",
           "budget_usd": int, "background": str}``
    resume:
        Original parsed resume dict from Component 2.  Used to populate
        ``user_has`` on each gap (what the user has adjacent to each gap).
        Pass ``None`` to leave all ``user_has`` fields null.

    Returns
    -------
    Gap list dict matching gap_list_spec.md v1.0, ready to pass directly to
    ``generate_roadmap()``.

    Example
    -------
    >>> gap_list = build_gap_list(
    ...     gap_result=analyze_gap(resume, role_profile),
    ...     target_role={"title": "Data Science Intern", "level": "internship", "role": "Data Scientist"},
    ...     user_context={"hours_per_week": 10, "target_date": "2027-05-01", "budget_usd": 0, "background": "Second-year Economics student."},
    ... )
    >>> from roadmap import generate_roadmap
    >>> roadmap = generate_roadmap(gap_list)
    """
    resume_skills: set[str] = (
        {normalize_skill(s) for s in (resume or {}).get("skills", [])}
    )

    gaps: list[dict] = []
    gap_id = 1

    # --- skill and tool gaps from skills_missing ---
    for entry in gap_result.get("skills_missing", []):
        peer_share = round(entry["frequency"] * 100)
        canonical = normalize_skill(entry["skill"])

        # user_has: note any adjacent skill from the resume that sounds related
        # (simple substring match — good enough until Component 2 adds richer data)
        adjacent = [s for s in resume_skills if s in canonical or canonical in s]
        user_has = f"Has: {', '.join(adjacent)}" if adjacent else None

        gaps.append({
            "gap_id": f"g{gap_id}",
            "item": entry["skill"],
            "category": "skill",
            "peer_share": peer_share,
            "severity": _severity(peer_share),
            "user_has": user_has,
        })
        gap_id += 1

    # --- experience gap ---
    experience_gap = gap_result.get("experience_gap", 0.0)
    if experience_gap > 0:
        gaps.append({
            "gap_id": f"g{gap_id}",
            "item": f"{experience_gap} more years of experience",
            "category": "experience",
            "peer_share": 100,   # experience is always expected
            "severity": "high" if experience_gap >= 1.0 else "medium",
            "user_has": (
                f"{resume.get('experience_years', 0.0)} years"
                if resume else None
            ),
        })
        gap_id += 1

    return {
        "schema_version": "1.0",
        "target_role": target_role,
        "gaps": gaps[:40],  # spec max is 40
        "user_context": user_context,
    }
