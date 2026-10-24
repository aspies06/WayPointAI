"""The Gradio app's input handling: resume, typed skills, both, or neither."""
import pytest

gr = pytest.importorskip("gradio")
app = pytest.importorskip("app")

SETTINGS = dict(level_label="Internship", experience_years=0, hours_per_week=10,
                timeline_days=180, budget_usd=100, background="")
SCRATCH = "starting from scratch"


@pytest.fixture(autouse=True)
def no_model(monkeypatch):
    monkeypatch.setenv("ROADMAP_AI", "0")


def run(uploaded_file=None, skills_text="", roles=("Software Engineer",)):
    return app.generate_career_roadmaps(uploaded_file, skills_text, list(roles), **SETTINGS)


def test_runs_without_a_resume_or_skills():
    out = run()
    assert SCRATCH in out and "## Software Engineer roadmap" in out


def test_typed_skills_count_like_resume_skills():
    none, typed = run(), run(skills_text="Python, Git, SQL")
    assert SCRATCH not in typed and typed != none
    assert "hires have Python " in none and "hires have Python " not in typed  # not a gap once you have it


def test_resume_and_typed_skills_combine(tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text("Skills: Python\n")
    both = run(str(resume), skills_text="Docker, Kubernetes")
    only_resume = run(str(resume))
    assert both != only_resume and SCRATCH not in both


def test_empty_optional_boxes_arrive_as_none():
    # Gradio passes None, not "", for text and number boxes left empty
    out = app.generate_career_roadmaps(None, None, ["Data Scientist"], "Internship", None, 10, 180, None, None)
    assert SCRATCH in out and "## Data Scientist roadmap" in out


def test_still_needs_a_role():
    with pytest.raises(gr.Error):
        run(roles=())
