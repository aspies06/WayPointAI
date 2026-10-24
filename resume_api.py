"""Story interview and resume drafting endpoints. Nothing here is stored.

Stories live only in the user's browser, encrypted (see web/src/storyVault.js). The browser sends
the stories a request needs; they're used in memory to build a preview or a draft, then dropped.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

import role_insights


router = APIRouter(prefix="/api/resume", tags=["Resume builder"])
MAX_STORIES = 50

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


class SavedStory(StoryInput):
    """A story from the browser's story bank, sent along for one request."""
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    narrative: str = Field(default="", max_length=10000)
    created_at: str = Field(default="", max_length=40)
    updated_at: str = Field(default="", max_length=40)


class ResumeProfile(InputModel):
    name: str = Field(default="", max_length=200)
    contact: str = Field(default="", max_length=500)
    education: str = Field(default="", max_length=2000)
    headline: str = Field(default="", max_length=300)


class GenerateInput(InputModel):
    stories: list[SavedStory] = Field(min_length=1, max_length=MAX_STORIES)
    job_description: str = Field(default="", max_length=15000)
    profile: ResumeProfile = Field(default_factory=ResumeProfile)
    max_stories: int = Field(default=5, ge=1, le=10, strict=True)
    role: str = Field(default="", max_length=60, description="Optional target role, one of the app's roles")

    @field_validator("stories")
    @classmethod
    def _unique_ids(cls, stories: list[SavedStory]) -> list[SavedStory]:
        if len({story.id for story in stories}) != len(stories):
            raise ValueError("Each story needs a different id.")
        return stories


def _known_role(role: str) -> str:
    if role and role not in role_insights.roles():
        raise HTTPException(status_code=400, detail="Choose a role from the list.")
    return role


def _draft(data: StoryInput) -> dict:
    from resume_generation import preview_story

    facts = data.model_dump()
    draft = preview_story(facts["answers"], facts["organization"], facts["dates"])
    return {**facts, **draft}


@router.get("/questions")
def questions() -> dict:
    return {"questions": QUESTIONS}


@router.get("/insights")
def insights(role: str) -> dict:
    """What people in the role do and the technologies in demand for it (O*NET). Public data."""
    data = role_insights.for_role(_known_role(role))
    if data is None:
        raise HTTPException(status_code=400, detail="Choose a role from the list.")
    return data


@router.post("/stories/preview")
def preview(data: StoryInput) -> dict:
    """The narrative a story would be saved with. The browser saves it; the server doesn't."""
    return _draft(data)


@router.post("/generate")
def generate(data: GenerateInput) -> dict:
    """A resume draft from the stories sent with this request, used in memory only."""
    from resume_generation import generate_resume

    stories = [story.model_dump() for story in data.stories]
    return generate_resume(stories, data.job_description, data.profile.model_dump(), data.max_stories,
                           role=_known_role(data.role) or None)
