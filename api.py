"""WayPointAI API for the React front end in web/.

    .venv/bin/python api.py           # http://127.0.0.1:8000  (interactive docs at /docs)

Then start the site: cd web && npm run dev (port 5173). The API only listens on
this computer, and only the site's own addresses may call it: Vite's dev server
(5173), its preview (4173) and Live Server on the built site (5500). Set
WAYPOINT_ALLOWED_ORIGINS (comma-separated) to allow others. Uploaded resumes are
read in memory and never stored. Experience stories are saved separately in the
local story bank (see resume_api.py). Set ROADMAP_AI=0 to skip the model's
personal tips and resume assistance.

Gap analysis on its own (no roadmap), for the other components and the docs page:
    GET  /api/roles     the built-in role profiles
    POST /api/analyze   a parsed resume + a role name or a full role profile -> gap analysis
Resume builder and story bank: /api/resume/... (resume_api.py)
"""
import os
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from career_pipeline import (
    LEVELS,
    MAX_UPLOAD_BYTES,
    ResumeError,
    combine_skills_text,
    extract_resume_text,
    gap_list_for_role,
)
from gap_analyzer import analyze_gap
from roadmap import generate_roadmap, intake
from roadmap.schemas import ROLES
from resume_api import router as resume_router
from role_profiles import ROLE_PROFILES

ALLOWED_ORIGINS = os.getenv(
    "WAYPOINT_ALLOWED_ORIGINS",
    ",".join(f"http://{host}:{port}" for port in (5173, 4173, 5500) for host in ("127.0.0.1", "localhost")),
).split(",")

app = FastAPI(title="WayPointAI API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])
app.include_router(resume_router)


@app.middleware("http")
async def private_story_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/resume/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/options")
def options() -> dict:
    """Everything the form needs, so the UI never hard-codes roles or questions."""
    return {
        "roles": list(ROLES),
        "levels": [{"label": label, "value": value} for label, value in LEVELS.items()],
        "workloads": [{"value": key, "hours": hours, "label": label}
                      for key, (hours, label) in intake.WORKLOADS.items()],
        "questions": intake.QUESTIONS,
        "date_format": intake.DATE_FORMAT,
    }


@app.exception_handler(RequestValidationError)
def _readable_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    """FastAPI's default 422 body is a list of dicts; the UI shows one plain sentence instead."""
    fields = ", ".join(str(e["loc"][-1]).replace("_", " ") for e in error.errors())
    return JSONResponse(status_code=400, content={"detail": f"Please check: {fields}."})


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


@app.post("/api/roadmaps")
def roadmaps(
    roles: Annotated[list[str], Form()] = [],
    # Required, but checked by intake below so a blank answer gets the friendly "Please answer" message
    hours_per_week: Annotated[str, Form()] = "",
    target_date: Annotated[str, Form()] = "",
    start_date: Annotated[str, Form()] = "",
    budget_usd: Annotated[str, Form()] = "",
    level: Annotated[str, Form()] = "entry",
    experience_years: Annotated[float, Form(ge=0, le=50)] = 0,
    background: Annotated[str, Form()] = "",
    skills_text: Annotated[str, Form()] = "",
    resume: Annotated[Optional[UploadFile], File()] = None,
) -> dict:
    """One roadmap per selected role. The time answers are required: we ask, never guess."""
    unknown = [r for r in roles if r not in ROLES]
    if unknown or not roles:
        raise _bad_request("Choose at least one of the listed roles.")
    if level not in LEVELS.values():
        raise _bad_request("Choose an experience level from the list.")
    try:
        ctx = intake.answers_to_context(
            {"hours_per_week": hours_per_week, "start_date": start_date,
             "target_date": target_date, "budget_usd": budget_usd},
            background=background)
    except intake.AvailabilityNeeded as error:
        raise _bad_request("Please answer: " + "; ".join(q["prompt"] for q in error.questions)) from error
    except ValueError as error:
        message = intake.error_message(error)
        raise _bad_request(message[:1].upper() + message[1:] + ".") from error

    resume_text = ""
    if resume is not None and resume.filename:
        content = resume.file.read(MAX_UPLOAD_BYTES + 1)
        try:
            resume_text = extract_resume_text(resume.filename, content)
        except ResumeError as error:
            raise _bad_request(str(error)) from error
    resume_text = combine_skills_text(resume_text, skills_text)

    results = []
    for role in dict.fromkeys(roles):  # each role once, in the order chosen
        gap_list = gap_list_for_role(resume_text, role, level, experience_years, ctx.model_dump(mode="json"))
        results.append({
            "role": role,
            "gap_names": {g["gap_id"]: g["item"] for g in gap_list["gaps"]},
            "roadmap": generate_roadmap(gap_list).model_dump(mode="json"),
        })
    return {"starting_from_scratch": not resume_text, "results": results}


# ---------- gap analysis on its own (Component 3) ----------
# Contracts: Component 1 sends role profiles, Component 2 sends parsed resumes,
# Components 4 and 5 read the result.

class SkillFrequency(BaseModel):
    """A skill and how often it appears in job postings (0-1)."""
    skill: str
    frequency: float = Field(ge=0.0, le=1.0)


class RoleProfileInput(BaseModel):
    """A role profile, shaped like the entries in role_profiles.ROLE_PROFILES."""
    role: str
    required_skills: list[SkillFrequency]
    preferred_skills: list[SkillFrequency] = Field(default_factory=list)
    avg_years_experience: float = Field(ge=0.0)
    common_education: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str
    field: str


class ResumeInput(BaseModel):
    """A parsed resume (Component 2)."""
    skills: list[str]
    education: list[EducationEntry] = Field(default_factory=list)
    experience_years: float = Field(ge=0.0, default=0.0)
    projects: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    """Send a full role_profile, or the name of a built-in role. role_profile wins if both are sent."""
    resume: ResumeInput
    role_profile: Optional[RoleProfileInput] = None
    role: Optional[str] = Field(default=None, description="A built-in role, e.g. 'Data Scientist'.")


class MissingSkill(BaseModel):
    skill: str
    priority: int = Field(ge=1)
    frequency: float = Field(ge=0.0, le=1.0)


class GapAnalysisResult(BaseModel):
    match_score: int = Field(ge=0, le=100)
    skills_present: list[str]
    skills_missing: list[MissingSkill]
    experience_gap: float = Field(ge=0.0)
    weak_areas: list[str]


@app.get("/api/roles")
def roles_list() -> dict:
    """Every built-in role profile, so other components never hard-code them."""
    return {"roles": [RoleProfileInput(**profile).model_dump() for profile in ROLE_PROFILES.values()]}


@app.post("/api/analyze", response_model=GapAnalysisResult)
def analyze(body: AnalyzeRequest) -> GapAnalysisResult:
    """Gap analysis between a parsed resume and a role profile (400 if neither role nor profile is sent)."""
    if body.role_profile is not None:
        role_profile = body.role_profile.model_dump()
    elif body.role is not None:
        if body.role not in ROLE_PROFILES:
            raise HTTPException(status_code=404,
                                detail=f"Role '{body.role}' not found. Available roles: {sorted(ROLE_PROFILES)}")
        role_profile = ROLE_PROFILES[body.role]
    else:
        raise _bad_request("Send either 'role_profile' or 'role'.")
    return GapAnalysisResult(**analyze_gap(body.resume.model_dump(), role_profile))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
