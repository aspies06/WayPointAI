import re
from io import BytesIO
from datetime import date, timedelta
from pathlib import Path

import gradio as gr
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from gap_analyzer import (
    SKILL_SYNONYMS,
    analyze_gap,
    build_gap_list,
    normalize_skill,
)
from roadmap import generate_roadmap
from roadmap import catalog
from roadmap.schemas import PHASE_LABELS, ROLES
from role_profiles import ROLE_PROFILES


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_RESUME_CHARACTERS = 18_000
LEVELS = {
    "Internship": "internship",
    "Entry / junior": "entry",
    "Mid-level": "mid",
    "Senior": "senior",
}


def extract_resume_text(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension == ".txt":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise gr.Error("Text resumes must use UTF-8 encoding.") from error
    elif extension == ".pdf":
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise gr.Error("The uploaded PDF is password-protected.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError as error:
            raise gr.Error("The uploaded file is not a readable PDF.") from error
    else:
        raise gr.Error("Upload a PDF or UTF-8 text file.")

    text = text.strip()
    if not text:
        raise gr.Error(
            "No selectable text was found. Scanned PDFs need OCR before upload."
        )
    return text[:MAX_RESUME_CHARACTERS]


def resume_skills_for_role(resume_text: str, role_profile: dict) -> list[str]:
    """Find profile skills explicitly mentioned in the resume text."""
    found: list[str] = []
    all_skills = role_profile["required_skills"] + role_profile["preferred_skills"]
    for entry in all_skills:
        skill = entry["skill"]
        canonical = normalize_skill(skill)
        variants = {skill}
        variants.update(
            alias
            for alias, normalized in SKILL_SYNONYMS.items()
            if normalized == canonical
        )
        for variant in variants:
            pattern = re.escape(variant).replace(r"\ ", r"\s+")
            if re.search(
                rf"(?<![a-z0-9]){pattern}(?![a-z0-9])",
                resume_text,
                flags=re.IGNORECASE,
            ):
                found.append(skill)
                break
    return list(dict.fromkeys(found))


def render_roadmap(gap_list: dict) -> str:
    roadmap = generate_roadmap(gap_list)
    resource_catalog = catalog.resources()
    gaps = {gap["gap_id"]: gap for gap in gap_list["gaps"]}

    sections = [
        f"## {roadmap.target_role.title} roadmap",
        f"**{roadmap.label}** | {roadmap.target_role.level.title()}",
        roadmap.summary,
        (
            f"**Estimated effort:** {roadmap.total_hours} hours "
            f"| **Available:** {roadmap.available_hours} hours"
        ),
    ]
    sections.extend(f"> **Note:** {warning}" for warning in roadmap.warnings)

    if roadmap.steps:
        for phase, phase_label in PHASE_LABELS.items():
            phase_steps = [step for step in roadmap.steps if step.phase == phase]
            if not phase_steps:
                continue
            sections.append(f"### {phase_label}")
            for step in phase_steps:
                sections.append(
                    f"#### {step.title} ({step.est_hours} hours)\n"
                    f"**Why:** {step.why}\n\n"
                    f"**Deliverable:** {step.deliverable}\n\n"
                    f"**Done when:** {step.done_when}"
                )
                if step.tip:
                    sections.append(f"**Personal tip:** {step.tip}")
                if step.resource_ids:
                    resources = []
                    for resource_id in step.resource_ids:
                        resource = resource_catalog[resource_id]
                        cost = (
                            "Free"
                            if resource["cost_usd"] == 0
                            else f"${resource['cost_usd']}"
                        )
                        resources.append(
                            f"- [{resource['name']}]({resource['url']}) · {cost}"
                        )
                    sections.append("**Resources:**\n" + "\n".join(resources))
    else:
        sections.append("No roadmap steps are needed for this role.")

    if roadmap.deferred:
        sections.append("### Deferred gaps")
        sections.append(
            "\n".join(
                f"- **{gaps[item.gap_id]['item']}:** {item.reason}"
                for item in roadmap.deferred
            )
        )
    return "\n\n".join(sections)


def generate_career_roadmaps(
    uploaded_file: str | None,
    skills_text: str | None,
    roles: list[str] | None,
    level_label: str,
    experience_years: float,
    hours_per_week: int,
    timeline_days: int,
    budget_usd: int,
    background: str,
) -> str:
    if not roles:
        raise gr.Error("Select at least one tech role.")

    resume_text = ""
    if uploaded_file:
        file_path = Path(uploaded_file)
        content = file_path.read_bytes()
        if len(content) > MAX_UPLOAD_BYTES:
            raise gr.Error("The uploaded file must be 10 MB or smaller.")
        resume_text = extract_resume_text(file_path.name, content)

    # Typed skills work with or without a resume; they're matched the same way.
    typed_skills = (skills_text or "").strip()
    resume_text = f"{resume_text}\n{typed_skills}".strip()[:MAX_RESUME_CHARACTERS]

    sections = []
    if not resume_text:
        sections.append(
            "> **Note:** No resume or skills were given, so these roadmaps "
            "assume you're starting from scratch."
        )
    for role in roles:
        role_profile = ROLE_PROFILES[role]
        resume = {
            "skills": resume_skills_for_role(resume_text, role_profile),
            "experience_years": experience_years or 0.0,
        }
        gap_result = analyze_gap(resume, role_profile)
        target_role = {
            "title": role,
            "level": LEVELS[level_label],
            "role": role,
        }
        user_context = {
            "hours_per_week": hours_per_week,
            "target_date": (date.today() + timedelta(days=timeline_days)).isoformat(),
            "budget_usd": budget_usd,
            "background": (background or "")[:600],  # Gradio sends None for an empty box
        }
        gap_list = build_gap_list(
            gap_result,
            target_role,
            user_context,
            resume=resume,
        )
        sections.append(render_roadmap(gap_list))

    return "\n\n---\n\n".join(sections)


with gr.Blocks(title="WayPointAI Career Roadmap") as demo:
    gr.Markdown("# WayPointAI Career Roadmap")
    gr.Markdown(
        "Upload a resume (or type your skills) and select one or more tech roles. "
        "WayPointAI checks for the skills you have, compares them with each role profile, "
        "and builds a roadmap from the curated catalog. Resume text is processed "
        "locally and is not sent to an inference service."
    )

    with gr.Row():
        resume_file = gr.File(
            label="Resume (PDF or UTF-8 text, optional)",
            file_types=[".pdf", ".txt"],
            type="filepath",
        )
        roles = gr.Dropdown(
            choices=list(ROLES),
            multiselect=True,
            label="Tech roles you are interested in",
        )

    skills_text = gr.Textbox(
        label="No resume? Enter your skills instead (optional)",
        placeholder="For example: Python, SQL, Git, Excel. Leave blank to start from scratch.",
        lines=2,
        max_lines=4,
    )

    with gr.Accordion("Roadmap preferences", open=False):
        level = gr.Dropdown(
            choices=list(LEVELS),
            value="Entry / junior",
            label="Experience level",
        )
        experience_years = gr.Number(
            value=0,
            minimum=0,
            maximum=50,
            label="Relevant years of experience",
        )
        hours_per_week = gr.Slider(
            minimum=1,
            maximum=80,
            value=10,
            step=1,
            label="Hours available per week",
        )
        timeline_days = gr.Slider(
            minimum=30,
            maximum=730,
            value=180,
            step=30,
            label="Days until target role",
        )
        budget_usd = gr.Number(
            value=0,
            minimum=0,
            maximum=100_000,
            label="Learning budget (USD)",
        )
        background = gr.Textbox(
            label="Background (optional)",
            placeholder="Education, current work, or other useful context",
            lines=2,
            max_lines=4,
        )

    submit = gr.Button("Generate roadmap", variant="primary")
    roadmap_output = gr.Markdown(label="Your roadmap")
    submit.click(
        fn=generate_career_roadmaps,
        inputs=[
            resume_file,
            skills_text,
            roles,
            level,
            experience_years,
            hours_per_week,
            timeline_days,
            budget_usd,
            background,
        ],
        outputs=roadmap_output,
    )


if __name__ == "__main__":
    demo.launch(share=True)
