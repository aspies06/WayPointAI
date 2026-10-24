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
SEV_RANK = {"high": 0, "medium": 1, "low": 2}
Priority = Literal["must_do", "should_do", "nice_to_have"]
PRIORITY_FROM_SEVERITY = {"high": "must_do", "medium": "should_do", "low": "nice_to_have"}
PRIORITY_LABELS = {"must_do": "Must do", "should_do": "Should do", "nice_to_have": "Nice to have"}
Benefit = Literal["certification", "certificate", "portfolio", "knowledge"]
BENEFIT_LABELS = {"certification": "Certification", "certificate": "Certificate of completion",
                  "portfolio": "Portfolio project", "knowledge": "Knowledge benefit (no certificate)"}

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


def _trim(value, limit: int):
    """Free text from other components can run long (a big resume, a pasted summary). Trimming it
    beats failing the user's whole roadmap; the cut is marked with an ellipsis."""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit - 1].rstrip() + "…"
    return value


class Gap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gap_id: str = Field(max_length=40)
    item: str = Field(max_length=120)
    category: Category
    peer_share: int = Field(ge=0, le=100, description="Percent of people in the role who have it. 0 means "
                            "no one does, so the gap is left out of the roadmap")
    severity: Severity
    user_has: Optional[str] = Field(default=None, max_length=200,
                                    description="What the user has instead, if anything")

    @field_validator("item", "user_has", mode="before")
    @classmethod
    def _trim_text(cls, v, info):
        return _trim(v, {"item": 120, "user_has": 200}[info.field_name])


class UserContext(BaseModel):
    """The user's own answers about their time (see intake.py). Ask before planning; never guess."""
    model_config = ConfigDict(extra="forbid")
    hours_per_week: int = Field(ge=1, le=80, description="The workload the user said they can sustain")
    start_date: Optional[date] = Field(default=None, description="When they can start; today if omitted")
    target_date: date
    budget_usd: Optional[int] = Field(default=None, ge=0, description="What the user wants to spend; None means no limit")
    background: str = Field(default="", max_length=600)

    @field_validator("background", mode="before")
    @classmethod
    def _trim_background(cls, v):
        return _trim(v, 600)

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.start_date and self.target_date <= self.start_date:
            raise ValueError("target_date must be after start_date")
        return self


class GapList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION
    target_role: TargetRole
    gaps: list[Gap] = Field(max_length=40)
    peer_share_measured: bool = Field(
        default=False, description="True only when peer_share comes from real hiring data. Otherwise the "
                                   "roadmap says 'most', 'some' or 'not many' instead of a made-up-looking percentage")
    user_context: Optional[UserContext] = Field(
        default=None, description="Missing until the user answers the availability questions; "
                                  "generate_roadmap() raises AvailabilityNeeded without it")


# ---------- output: roadmap ----------

class ResourceLink(BaseModel):
    """A catalog resource resolved for display. Links only ever come from data/catalog.json."""
    id: str
    name: str
    provider: str
    url: str
    cost_usd: int
    type: str


class Suggestion(BaseModel):
    """Something worth considering instead of, or on top of, the plan, even if it's over budget."""
    kind: Literal["credential", "cheaper", "faster"]
    resource_id: str
    reason: str
    resource: Optional[ResourceLink] = None  # filled in from the catalog for display


class Step(BaseModel):
    step_id: str
    title: str
    priority: Priority = "should_do"
    phase: Phase
    type: StepType
    gap_ids: list[str]
    why: str
    deliverable: str
    done_when: str
    resource_ids: list[str]
    project_id: Optional[str] = None
    est_hours: int
    cost_usd: int = Field(default=0, description="New spending this step needs; resources bought earlier count as $0")
    depends_on: list[str]
    tip: Optional[str] = Field(default=None, description="Personal advice from the local model, if it passed checks")
    start_date: Optional[date] = Field(default=None, description="Scheduled start at the user's hours/week; "
                                       "None for optional items")
    end_date: Optional[date] = None
    resources: list[ResourceLink] = Field(default=[], description="resource_ids resolved to names and links")
    optional_because: Optional[Literal["time", "budget"]] = Field(
        default=None, description="Set on optional items: why it isn't on the timeline")
    benefit: Benefit = Field(default="knowledge", description="What finishing it earns you")
    shortened_from: Optional[int] = Field(default=None, description="Full hours, if this step was cut to fit the time")
    scope_note: Optional[str] = Field(default=None, description="Plain-language note when a step was split or reshaped")
    suggestions: list[Suggestion] = Field(default=[], description="Worth considering, even outside the budget")


class Deferred(BaseModel):
    gap_id: str
    reason: str


class ExperienceAdvice(BaseModel):
    """Years of work experience can't be studied for, so they're not a timeline step.
    The roadmap says plainly what to do instead (usually: get an entry-level job)."""
    gap_id: str
    years: Optional[float] = None
    message: str


class RoadmapDraft(BaseModel):
    """The plan. guardrails.py enforces the rules on it."""
    summary: str
    steps: list[Step]
    deferred: list[Deferred]
    optional: list[Step] = Field(default=[], description="Steps that don't fit the user's time or budget, kept "
                                 "so the UI can offer them behind a button. Their gaps are also in deferred.")
    experience: Optional[ExperienceAdvice] = Field(
        default=None, description="Shown above the timeline when the real need is work experience")


class Roadmap(RoadmapDraft):
    schema_version: str = SCHEMA_VERSION
    target_role: TargetRole
    source: Source
    label: str = Field(description="Small UI label: 'Personalized roadmap' or 'Basic roadmap'")
    total_hours: int
    available_hours: int
    hours_per_week: int
    start_date: date
    finish_date: date = Field(description="When the last planned step ends at the user's pace")
    target_date: date
    warnings: list[str] = []
