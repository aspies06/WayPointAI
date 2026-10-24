"""Resume in, gap list out: the steps behind the API (api.py).

Reads a resume (PDF or UTF-8 text), finds which role-profile skills it
mentions, and turns the gaps into a gap list for roadmap.generate_roadmap().
No UI framework imports here, so any front end can use it.
"""
import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from gap_analyzer import SKILL_SYNONYMS, analyze_gap, build_gap_list, normalize_skill
from role_profiles import ROLE_PROFILES

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_RESUME_CHARACTERS = 18_000
LEVELS = {
    "Internship": "internship",
    "Entry / junior": "entry",
    "Mid-level": "mid",
    "Senior": "senior",
}


class ResumeError(ValueError):
    """The upload can't be read; the message is safe to show the user."""


def extract_resume_text(filename: str, content: bytes) -> str:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ResumeError("The uploaded file must be 10 MB or smaller.")
    extension = Path(filename).suffix.lower()
    if extension == ".txt":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ResumeError("Text resumes must use UTF-8 encoding.") from error
    elif extension == ".pdf":
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise ResumeError("The uploaded PDF is password-protected.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError as error:
            raise ResumeError("The uploaded file is not a readable PDF.") from error
    else:
        raise ResumeError("Upload a PDF or UTF-8 text file.")

    text = text.strip()
    if not text:
        raise ResumeError("No selectable text was found. Scanned PDFs need OCR before upload.")
    return text[:MAX_RESUME_CHARACTERS]


def combine_skills_text(resume_text: str, skills_text: str | None) -> str:
    """Typed skills work with or without a resume; they're matched the same way."""
    return f"{resume_text}\n{(skills_text or '').strip()}".strip()[:MAX_RESUME_CHARACTERS]


def resume_skills_for_role(resume_text: str, role_profile: dict) -> list[str]:
    """Find profile skills explicitly mentioned in the resume text."""
    found: list[str] = []
    all_skills = role_profile["required_skills"] + role_profile["preferred_skills"]
    for entry in all_skills:
        skill = entry["skill"]
        canonical = normalize_skill(skill)
        variants = {skill, *entry.get("aliases", [])}
        variants.update(
            alias
            for alias, normalized in SKILL_SYNONYMS.items()
            if normalized == canonical
        )
        for variant in variants:
            pattern = re.escape(variant).replace(r"\ ", r"\s+")
            # Short names ("C", "R", "Go") only count when written that way, not "go" or "r".
            flags = 0 if len(variant) <= 2 else re.IGNORECASE
            if re.search(rf"(?<![A-Za-z0-9+#]){pattern}(?![A-Za-z0-9+#])", resume_text, flags=flags):
                found.append(skill)
                break
    return list(dict.fromkeys(found))


def gap_list_for_role(resume_text: str, role: str, level: str, experience_years: float,
                      user_context: dict) -> dict:
    """The gap list for one role. `level` is a roadmap level value ("internship", "entry", ...)."""
    role_profile = ROLE_PROFILES[role]
    if level in ("internship", "entry"):
        # O*NET's experience figures describe workers at every career stage, so they'd overstate
        # what an internship or entry-level job asks for. Don't turn them into a gap.
        role_profile = {**role_profile, "avg_years_experience": 0.0}
    resume = {
        "skills": resume_skills_for_role(resume_text, role_profile),
        "experience_years": experience_years or 0.0,
    }
    return build_gap_list(
        analyze_gap(resume, role_profile),
        {"title": role, "level": level, "role": role},
        user_context,
        resume=resume,
    )
