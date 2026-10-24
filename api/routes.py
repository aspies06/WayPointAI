"""
api/routes.py
-------------
FastAPI route definitions for WayPointAI (Component 3, Person B).

Endpoints
---------
POST /analyze
    Accepts a parsed resume and a role profile (or a role name for the
    built-in stubs) and returns a gap analysis result.  This is the primary
    integration point: Component 2 feeds in, Components 4 and 5 consume out.

GET /roles
    Returns the list of supported role names together with their stub profiles.
    Lets Component 5 (frontend) populate a role picker without hardcoding names,
    and lets Component 4 (LLM / roadmap) know what's available.
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from gap_analyzer import analyze_gap
from role_profiles import ROLE_PROFILES

from .models import AnalyzeRequest, GapAnalysisResult, MissingSkill, RoleProfileInput

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------


@router.post(
    "/analyze",
    response_model=GapAnalysisResult,
    summary="Run gap analysis between a resume and a role profile",
    response_description="Gap analysis result ready for Components 4 and 5",
)
def analyze(body: AnalyzeRequest) -> GapAnalysisResult:
    """
    Run gap analysis between a parsed resume and a role profile.

    Supply either:
    - ``role_profile`` — a full role profile object (from Component 1), or
    - ``role`` — the name of a built-in stub role (e.g. ``"Data Scientist"``)

    If both are provided, ``role_profile`` wins.
    If neither is provided, a **400** is returned.
    """
    # Resolve the role profile
    if body.role_profile is not None:
        role_profile = body.role_profile.model_dump()
    elif body.role is not None:
        if body.role not in ROLE_PROFILES:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Role '{body.role}' not found. "
                    f"Available roles: {sorted(ROLE_PROFILES)}"
                ),
            )
        role_profile = ROLE_PROFILES[body.role]
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'role_profile' or 'role' in the request body.",
        )

    resume = body.resume.model_dump()

    raw = analyze_gap(resume, role_profile)

    return GapAnalysisResult(
        match_score=raw["match_score"],
        skills_present=raw["skills_present"],
        skills_missing=[MissingSkill(**s) for s in raw["skills_missing"]],
        experience_gap=raw["experience_gap"],
        weak_areas=raw["weak_areas"],
    )


# ---------------------------------------------------------------------------
# GET /roles
# ---------------------------------------------------------------------------


@router.get(
    "/roles",
    summary="List all supported roles",
    response_description="Mapping of role names to their full stub profiles",
)
def list_roles() -> Dict[str, Any]:
    """
    Return the full list of supported roles and their stub profiles.

    The response is a dict keyed by role name::

        {
            "roles": [
                {
                    "role": "Data Scientist",
                    "required_skills": [...],
                    "preferred_skills": [...],
                    "avg_years_experience": 3.0,
                    "common_education": [...]
                },
                ...
            ]
        }

    Component 5 uses this to populate the role picker.
    Component 4 uses this to know which roles are available.
    """
    return {
        "roles": [
            RoleProfileInput(**profile).model_dump()
            for profile in ROLE_PROFILES.values()
        ]
    }
