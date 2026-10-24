"""Data contracts for the roadmap module.

GapList is what the backend sends in. Roadmap is what we send out to the UI.
RoadmapDraft is the plan itself (built by planner.py); Roadmap adds metadata.
See docs/gap_list_spec.md for the human-readable version.
"""
import re
from datetime import date
from typing import Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"

Level = Literal["internship", "entry", "mid", "senior"]
# The catalog and templates are built for these. Senior is accepted but planned as mid.
FOCUS_LEVELS = ("internship", "entry", "mid")
LEVEL_ALIASES = {"intern": "internship", "junior": "entry", "entry-level": "entry",
                 "entry level": "entry", "new grad": "entry", "mid-level": "mid", "intermediate": "mid"}
Role = Literal["Software Engineer", "AI/ML Engineer", "Data Scientist", "Security Engineer",
               "Computer Engineer", "IT Support Specialist", "Hardware Engineer", "QA Engineer",
               "Product Manager"]
ROLES: tuple[str, ...] = get_args(Role)
# Title words that identify each role, for when the backend sends only a title.
# The longest alias found in the title wins: "Embedded Software Engineer" is a Computer Engineer.
ROLE_ALIASES: dict[str, list[str]] = {
    "Software Engineer": ["software engineer", "software engineering", "software developer", "swe",
                          "developer", "programmer", "backend engineer", "frontend engineer",
                          "full stack", "full-stack", "web developer", "mobile developer"],
    "AI/ML Engineer": ["ai/ml", "ai engineer", "ml engineer", "machine learning", "deep learning",
                       "mlops", "llm engineer", "applied scientist", "ai/ml engineer"],
    "Data Scientist": ["data scientist", "data science", "data analyst", "data analytics",
                       "analytics engineer", "business intelligence", "bi analyst"],
    "Security Engineer": ["security engineer", "security engineering", "security analyst", "cybersecurity",
                          "cyber security", "soc analyst", "appsec", "application security",
                          "penetration tester", "pentester", "infosec", "information security"],
    "Computer Engineer": ["computer engineer", "computer engineering", "embedded", "firmware",
                          "embedded software engineer", "embedded systems"],
    "IT Support Specialist": ["it support", "help desk", "helpdesk", "desktop support", "technical support",
                              "it specialist", "it technician", "systems administrator", "sysadmin",
                              "system administrator"],
    "Hardware Engineer": ["hardware engineer", "hardware engineering", "electrical engineer",
                          "electrical engineering", "pcb", "fpga", "asic", "hardware design"],
    "QA Engineer": ["qa", "quality assurance", "test engineer", "sdet", "software tester",
                    "test automation", "quality engineer"],
    "Product Manager": ["product manager", "product management", "apm", "pm", "product owner"],
}


def _words(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9/+]+", " ", text.lower()).strip() + " "


def infer_role(title: str) -> Optional[str]:
    """Best supported role for a free-text job title, or None."""
    t = _words(title)
    hits = [(len(a), role) for role, aliases in ROLE_ALIASES.items() for a in aliases if _words(a) in t]
    return max(hits)[1] if hits else None


Category = Literal["cert", "skill", "tool", "experience", "education"]
Severity = Literal["high", "medium", "low"]
StepType = Literal["cert", "project", "course", "experience", "networking"]
Phase = Literal["first_30_days", "days_30_90", "days_90_plus"]
Source = Literal["ai", "cache", "demo", "basic"]

PHASE_LABELS = {
    "first_30_days": "First 30 days",
    "days_30_90": "Days 30-90",
    "days_90_plus": "90+ days",
}


# ---------- input: gap list ----------

class TargetRole(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=120)
    level: Level = "entry"
    role: Optional[Role] = Field(default=None, description="One of ROLES; inferred from title if omitted")

    @field_validator("role", mode="before")
    @classmethod
    def _canonical_role(cls, v):
        if isinstance(v, str):
            return next((r for r in ROLES if r.lower() == v.strip().lower()), v)
        return v

    @model_validator(mode="after")
    def _fill_role(self):
        if self.role is None:
            self.role = infer_role(self.title)
        return self

    @field_validator("level", mode="before")
    @classmethod
    def _canonical_level(cls, v):
        """Backends say 'junior', 'Intern', 'Mid-Level'... map them to one value."""
        if isinstance(v, str):
            v = v.strip().lower()
            return LEVEL_ALIASES.get(v, v)
        return v


class Gap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gap_id: str = Field(max_length=40)
    item: str = Field(max_length=120)
    category: Category
    peer_share: int = Field(ge=0, le=100, description="Percent of people in the role who have it")
    severity: Severity
    user_has: Optional[str] = Field(default=None, max_length=200,
                                    description="What the user has instead, if anything")


class UserContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours_per_week: int = Field(ge=1, le=80)
    target_date: date
    budget_usd: int = Field(ge=0)
    background: str = Field(default="", max_length=600)


class GapList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION
    target_role: TargetRole
    gaps: list[Gap] = Field(max_length=40)
    user_context: UserContext


# ---------- output: roadmap ----------

class Step(BaseModel):
    step_id: str
    title: str
    phase: Phase
    type: StepType
    gap_ids: list[str]
    why: str
    deliverable: str
    done_when: str
    resource_ids: list[str]
    project_id: Optional[str] = None
    est_hours: int
    depends_on: list[str]
    tip: Optional[str] = Field(default=None, description="Personal advice from the local model, if it passed checks")


class Deferred(BaseModel):
    gap_id: str
    reason: str


class RoadmapDraft(BaseModel):
    """The plan. guardrails.py enforces the rules on it."""
    summary: str
    steps: list[Step]
    deferred: list[Deferred]


class Roadmap(RoadmapDraft):
    schema_version: str = SCHEMA_VERSION
    target_role: TargetRole
    source: Source
    label: str = Field(description="Small UI label: 'Personalized roadmap' or 'Basic roadmap'")
    total_hours: int
    available_hours: int
    warnings: list[str] = []
