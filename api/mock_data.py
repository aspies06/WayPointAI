"""
api/mock_data.py
----------------
Mock request bodies and expected responses for the WayPointAI API.

Purpose
-------
- Component 5 (frontend) can hit these fixtures directly while the real
  resume parser (Component 2) is still being built.
- Used as pytest parametrize data in tests/test_api.py.
- Paste any ``MOCK_REQUESTS`` entry straight into the interactive docs at
  /docs to see a real response.

Fixtures
--------
MOCK_REQUESTS  — list of AnalyzeRequest-compatible dicts, one per scenario.
MOCK_ROLE      — a minimal custom RoleProfileInput dict (not in ROLE_PROFILES)
                 useful for testing the role_profile path.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Re-usable resume snippets
# ---------------------------------------------------------------------------

_STRONG_DS_RESUME = {
    "skills": ["Python", "SQL", "Machine Learning", "Pandas", "Scikit-learn"],
    "education": [{"degree": "BSc", "field": "Statistics"}],
    "experience_years": 2.5,
    "projects": ["Built a churn prediction model", "Created a sales forecasting dashboard"],
}

_WEAK_DS_RESUME = {
    "skills": ["Python", "Excel", "Tableau"],
    "education": [{"degree": "BSc", "field": "Economics"}],
    "experience_years": 1.5,
    "projects": ["Built a sales dashboard"],
}

_SWE_RESUME = {
    "skills": ["Python", "Git", "REST APIs", "Docker"],
    "education": [{"degree": "BSc", "field": "Computer Science"}],
    "experience_years": 1.0,
    "projects": ["Open-source CLI tool", "REST API for a student project"],
}

_NO_SKILLS_RESUME = {
    "skills": [],
    "education": [{"degree": "BA", "field": "History"}],
    "experience_years": 0.0,
    "projects": [],
}

# ---------------------------------------------------------------------------
# MOCK_REQUESTS — ready-to-POST dicts (role lookup path)
# ---------------------------------------------------------------------------

MOCK_REQUESTS: list[dict] = [
    {
        "_name": "data_scientist_strong",
        "_description": "Candidate with most required DS skills, slight experience gap",
        "resume": _STRONG_DS_RESUME,
        "role": "Data Scientist",
    },
    {
        "_name": "data_scientist_weak",
        "_description": "Candidate with few matching skills and large experience gap",
        "resume": _WEAK_DS_RESUME,
        "role": "Data Scientist",
    },
    {
        "_name": "software_engineer_partial",
        "_description": "SWE candidate missing DSA, SQL, System Design",
        "resume": _SWE_RESUME,
        "role": "Software Engineer",
    },
    {
        "_name": "career_changer_no_skills",
        "_description": "Complete career changer with no matching technical skills",
        "resume": _NO_SKILLS_RESUME,
        "role": "Software Engineer",
    },
]

# ---------------------------------------------------------------------------
# MOCK_ROLE — custom role profile (role_profile path)
# ---------------------------------------------------------------------------

MOCK_ROLE: dict = {
    "resume": _WEAK_DS_RESUME,
    "role_profile": {
        "role": "Analytics Engineer",
        "required_skills": [
            {"skill": "SQL",    "frequency": 0.95},
            {"skill": "dbt",    "frequency": 0.88},
            {"skill": "Python", "frequency": 0.75},
        ],
        "preferred_skills": [
            {"skill": "Tableau",  "frequency": 0.40},
            {"skill": "Spark",    "frequency": 0.35},
        ],
        "avg_years_experience": 2.0,
        "common_education": ["Computer Science", "Statistics"],
    },
}
