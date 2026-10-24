"""WayPointAI API for the React front end in web/.

    .venv/bin/python api.py           # http://127.0.0.1:8000  (interactive docs at /docs)

Then open web/index.html with VS Code's Live Server (port 5500). The API only
listens on this computer, and only the Live Server origins may call it; set
WAYPOINT_ALLOWED_ORIGINS (comma-separated) to allow others. Uploaded resumes are
read in memory. Experience stories are saved separately in the local story bank.
Set ROADMAP_AI=0 to skip the model's personal tips and resume assistance.
"""
import os
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from career_pipeline import (
    LEVELS,
    MAX_UPLOAD_BYTES,
    ResumeError,
    combine_skills_text,
    extract_resume_text,
    gap_list_for_role,
)
from roadmap import generate_roadmap, intake
from roadmap.schemas import ROLES
from resume_api import router as resume_router

ALLOWED_ORIGINS = os.getenv(
    "WAYPOINT_ALLOWED_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
