"""
api/models.py
-------------
Pydantic request and response models for the WayPointAI FastAPI layer.

These schemas are the shared contracts between:
  - Component 1 → /analyze (role_profile input)
  - Component 2 → /analyze (resume input)
  - /analyze     → Components 4 & 5 (gap analysis output)
  - /roles       → Components 4 & 5 (available roles list)
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


class SkillFrequency(BaseModel):
    """A skill together with how often it appears in job postings (0-1)."""

    skill: str
    frequency: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Input 1 — Role Profile (produced by Component 1)
# ---------------------------------------------------------------------------


class RoleProfileInput(BaseModel):
    """Role profile as produced by Component 1 (data engineering)."""

    role: str
    required_skills: List[SkillFrequency]
    preferred_skills: List[SkillFrequency] = Field(default_factory=list)
    avg_years_experience: float = Field(ge=0.0)
    common_education: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Input 2 — Parsed Resume (produced by Component 2)
# ---------------------------------------------------------------------------


class EducationEntry(BaseModel):
    degree: str
    field: str


class ResumeInput(BaseModel):
    """Parsed resume object produced by Component 2 (resume parser)."""

    skills: List[str]
    education: List[EducationEntry] = Field(default_factory=list)
    experience_years: float = Field(ge=0.0, default=0.0)
    projects: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /analyze request body
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """
    Request body for ``POST /analyze``.

    Either supply ``role_profile`` directly (from Component 1) **or** supply
    a ``role`` name to look up the built-in stub profile from
    ``role_profiles.ROLE_PROFILES``.  If both are given, ``role_profile``
    takes precedence.
    """

    resume: ResumeInput
    role_profile: Optional[RoleProfileInput] = None
    role: Optional[str] = Field(
        default=None,
        description=(
            "Name of a built-in role (e.g. 'Data Scientist'). "
            "Ignored when role_profile is supplied."
        ),
    )


# ---------------------------------------------------------------------------
# Output — Gap Analysis Result (consumed by Components 4 & 5)
# ---------------------------------------------------------------------------


class MissingSkill(BaseModel):
    skill: str
    priority: int = Field(ge=1)
    frequency: float = Field(ge=0.0, le=1.0)


class GapAnalysisResult(BaseModel):
    """Gap analysis result returned by ``POST /analyze``."""

    match_score: int = Field(ge=0, le=100)
    skills_present: List[str]
    skills_missing: List[MissingSkill]
    experience_gap: float = Field(ge=0.0)
    weak_areas: List[str]
