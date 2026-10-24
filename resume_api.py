"""Story-bank interview, persistence, and resume drafting endpoints."""
from contextlib import contextmanager
import re
import sqlite3
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

import resume_store


router = APIRouter(prefix="/api/resume", tags=["Resume story bank"])
_bearer = HTTPBearer(auto_error=False)

QUESTIONS = [
    {"id": "context", "prompt": "What was your role or project?",
     "hint": "A job, class project, volunteer role, or personal project all count.", "required": True},
    {"id": "problem", "prompt": "What problem were you trying to solve?",
     "hint": "One or two sentences about the challenge or goal.", "required": True},
    {"id": "actions", "prompt": "What did you personally do?",
     "hint": "Describe your own contribution, even if you worked with a team.", "required": True},
    {"id": "tools", "prompt": "What tools or skills did you use?",
     "hint": "List a few tools, methods, or skills. Skip this if none apply.", "required": False},
    {"id": "outcome", "prompt": "What changed because of your work?",
     "hint": "Share a result, feedback, or lesson. Include numbers only if you know them; skip if still in progress.",
     "required": False},
]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StoryAnswers(InputModel):
    context: str = Field(min_length=1, max_length=600)
    problem: str = Field(min_length=1, max_length=2000)
    actions: str = Field(min_length=1, max_length=3000)
    tools: str = Field(default="", max_length=1000)
    outcome: str = Field(default="", max_length=2000)


class StoryInput(InputModel):
    answers: StoryAnswers
    organization: str = Field(default="", max_length=200)
    dates: str = Field(default="", max_length=100)


class ResumeProfile(InputModel):
    name: str = Field(default="", max_length=200)
    contact: str = Field(default="", max_length=500)
    education: str = Field(default="", max_length=2000)
    headline: str = Field(default="", max_length=300)


class GenerateInput(InputModel):
    job_description: str = Field(default="", max_length=15000)
    profile: ResumeProfile = Field(default_factory=ResumeProfile)
    max_stories: int = Field(default=5, ge=1, le=10, strict=True)


@contextmanager
def _storage_errors():
    try:
        yield
    except (sqlite3.Error, OSError) as error:
        raise HTTPException(status_code=503, detail="Your story bank is temporarily unavailable. Please try again.") from error


def library_owner(credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]) -> str:
    key = credentials.credentials if credentials else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", key):
        raise HTTPException(status_code=401, detail="Open your story bank to continue.",
                            headers={"WWW-Authenticate": "Bearer"})
    digest = resume_store.key_digest(key)
    with _storage_errors():
        exists = resume_store.library_exists(digest)
    if not exists:
        raise HTTPException(status_code=401, detail="This story bank key is no longer valid.",
                            headers={"WWW-Authenticate": "Bearer"})
    return digest


Owner = Annotated[str, Depends(library_owner)]


def _draft(data: StoryInput) -> dict:
    from resume_generation import preview_story

    facts = data.model_dump()
    draft = preview_story(facts["answers"], facts["organization"], facts["dates"])
    return {**facts, **draft}


@router.get("/questions")
def questions() -> dict:
    return {"questions": QUESTIONS}


@router.post("/library", status_code=201)
def new_library() -> dict:
    with _storage_errors():
        key = resume_store.create_library()
    return {"library_key": key}


@router.get("/stories")
def stories(owner: Owner) -> dict:
    with _storage_errors():
        saved = resume_store.list_stories(owner)
    return {"stories": saved}


@router.post("/stories/preview")
def preview(data: StoryInput, owner: Owner) -> dict:
    return _draft(data)


@router.post("/stories", status_code=201)
def save_story(data: StoryInput, owner: Owner) -> dict:
    draft = _draft(data)
    with _storage_errors():
        return resume_store.create_story(owner, draft)


@router.put("/stories/{story_id}")
def edit_story(story_id: str, data: StoryInput, owner: Owner) -> dict:
    draft = _draft(data)
    with _storage_errors():
        saved = resume_store.update_story(owner, story_id, draft)
    if saved is None:
        raise HTTPException(status_code=404, detail="That story was not found in your story bank.")
    return saved


@router.delete("/stories/{story_id}")
def remove_story(story_id: str, owner: Owner) -> dict:
    with _storage_errors():
        deleted = resume_store.delete_story(owner, story_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="That story was not found in your story bank.")
    return {"deleted": True}


@router.post("/generate")
def generate(data: GenerateInput, owner: Owner) -> dict:
    from resume_generation import generate_resume

    with _storage_errors():
        saved = resume_store.list_stories(owner)
    if not saved:
        raise HTTPException(status_code=400, detail="Save at least one experience story before drafting your resume.")
    return generate_resume(saved, data.job_description, data.profile.model_dump(), data.max_stories)
