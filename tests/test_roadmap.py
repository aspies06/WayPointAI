"""Offline tests: no model download or network needed."""
import threading
from datetime import date
from pathlib import Path
import pytest

from roadmap import GapList, catalog, generate, local_model
from roadmap.guardrails import check
from roadmap.planner import build_plan
from roadmap.schemas import ROLES, Deferred, RoadmapDraft, Step, infer_role

TODAY = date(2026, 10, 23)
PERSONAS = sorted((Path(__file__).parent / "personas").glob("*.json"))


def load(name: str) -> GapList:
    return GapList.model_validate_json((Path(__file__).parent / "personas" / f"{name}.json").read_text())


def good_step(**kw) -> Step:
    base = dict(step_id="S1", title="Solve a structured set of coding problems", phase="first_30_days",
                type="project", gap_ids=["g2"], why="75% of Software Engineer hires practice DSA.",
                deliverable="GitHub repo with 75 solved problems and notes on each pattern",
                done_when="All 75 problems pass and each has a written time/space analysis",
                resource_ids=["R-NEETCODE"], est_hours=60, depends_on=[])
    return Step(**{**base, **kw})


def draft_for(gl: GapList, steps: list[Step]) -> RoadmapDraft:
    covered = {g for s in steps for g in s.gap_ids}
    return RoadmapDraft(summary="x", steps=steps,
                        deferred=[Deferred(gap_id=g.gap_id, reason="later") for g in gl.gaps if g.gap_id not in covered])


def titles(gl: GapList) -> list[str]:
    return [s.title for s in build_plan(gl, TODAY).steps]


# ---------- guardrails catch bad output ----------

def test_clean_draft_passes():
    gl = load("swe_new_grad")
    errors, _ = check(draft_for(gl, [good_step()]), gl, TODAY)
    assert errors == []


@pytest.mark.parametrize("step, expected", [
    (good_step(resource_ids=["R-MADE-UP"]), "not in the catalog"),
    (good_step(gap_ids=["g99"]), "unknown gap_id"),
    (good_step(gap_ids=[]), "cites no gap_id"),
    (good_step(why="You should gain experience in algorithms."), "vague phrase"),
    (good_step(deliverable="Do it"), "deliverable"),
    (good_step(est_hours=5000), "hours"),
    (good_step(depends_on=["S1"]), "loop"),
    (good_step(project_id="P-NOPE"), "project_id"),
    (good_step(tip="See https://example.com for more"), "URL"),
])
def test_guardrails_reject(step, expected):
    gl = load("swe_new_grad")
    errors, _ = check(draft_for(gl, [step]), gl, TODAY)
    assert any(expected in e for e in errors), errors


def test_silently_dropped_gap_is_an_error():
    gl = load("swe_new_grad")
    errors, _ = check(RoadmapDraft(summary="x", steps=[good_step()], deferred=[]), gl, TODAY)
    assert any("neither covered nor deferred" in e for e in errors)


# ---------- the planner always passes ----------

@pytest.mark.parametrize("path", PERSONAS, ids=lambda p: p.stem)
def test_plan_passes_guardrails(path):
    gl = GapList.model_validate_json(path.read_text())
    errors, warnings = check(build_plan(gl, TODAY), gl, TODAY)
    assert errors == []
    assert not any("budget" in w for w in warnings)


def test_injection_text_is_just_data():
    gl = load("injection")
    d = build_plan(gl, TODAY)
    assert d.steps, "injection must not zero out the plan"
    assert "http" not in d.model_dump_json()


def test_catalog_references_are_valid():
    for p in catalog.projects().values():
        assert all(r in catalog.resources() for r in p["resource_ids"]), p["id"]
        assert set(p.get("levels", catalog.LEVELS)) <= set(catalog.LEVELS), p["id"]
    for r in catalog.resources().values():
        assert r["level"] in catalog.LEVELS, r["id"]
    for e in [*catalog.projects().values(), *catalog.resources().values()]:
        assert set(e.get("roles", ROLES)) <= set(ROLES), e["id"]


# ---------- roles ----------

@pytest.mark.parametrize("role", ROLES)
def test_every_role_has_catalog_coverage(role):
    personas = [gl for p in PERSONAS if p.stem != "no_catalog_match"
                if (gl := GapList.model_validate_json(p.read_text())).target_role.role == role and gl.gaps]
    assert personas, f"no test persona for {role}"
    for gl in personas:
        # Deferring for time or money is fine; deferring because the catalog has nothing is a gap in coverage.
        missing = [d.gap_id for d in build_plan(gl, TODAY).deferred if d.reason.startswith("No curated")]
        assert len(missing) <= len(gl.gaps) / 4, (gl.target_role.title, missing)


@pytest.mark.parametrize("path", PERSONAS, ids=lambda p: p.stem)
def test_plans_only_use_on_role_projects(path):
    gl = GapList.model_validate_json(path.read_text())
    for s in build_plan(gl, TODAY).steps:
        if s.project_id:
            roles = catalog.projects()[s.project_id].get("roles", ROLES)
            assert gl.target_role.role in roles, (s.project_id, gl.target_role.role)


@pytest.mark.parametrize("title, role", [
    ("Software Engineering Intern", "Software Engineer"), ("Machine Learning Engineer", "AI/ML Engineer"),
    ("Data Analyst", "Data Scientist"), ("Cybersecurity Analyst", "Security Engineer"),
    ("Embedded Software Engineer", "Computer Engineer"), ("Help Desk Technician", "IT Support Specialist"),
    ("Electrical Engineer", "Hardware Engineer"), ("SDET", "QA Engineer"),
    ("Associate Product Manager", "Product Manager"), ("Pastry Chef", None),
])
def test_role_inferred_from_title(title, role):
    assert infer_role(title) == role


def test_explicit_role_wins_and_ignores_case():
    gl = load("swe_new_grad").model_dump(mode="json")
    gl["target_role"] = {"title": "Platform Intern", "level": "internship", "role": "qa engineer"}
    assert GapList.model_validate(gl).target_role.role == "QA Engineer"
    gl["target_role"]["role"] = "Astronaut"
    with pytest.raises(Exception):
        GapList.model_validate(gl)


def test_same_gap_differs_by_role():
    def plan_for(role):
        gl = load("swe_new_grad")
        gl.target_role.role = role
        gl.gaps = [gl.gaps[0].model_copy(update={"item": "Python scripting"})]
        return build_plan(gl, TODAY).steps[0]
    assert plan_for("Security Engineer").project_id == "P-PYTHON-IOC"
    assert plan_for("IT Support Specialist").project_id is None  # a course, not a security project


# ---------- levels: internship, junior, mid ----------

@pytest.mark.parametrize("raw, level", [
    ("junior", "entry"), ("Junior", "entry"), ("new grad", "entry"),
    ("intern", "internship"), ("Mid-Level", "mid"), ("senior", "senior"),
])
def test_level_aliases(raw, level):
    gl = load("swe_new_grad").model_dump(mode="json")
    gl["target_role"]["level"] = raw
    assert GapList.model_validate(gl).target_role.level == level


def test_unknown_level_is_rejected():
    gl = load("swe_new_grad").model_dump(mode="json")
    gl["target_role"]["level"] = "wizard"
    with pytest.raises(Exception):
        GapList.model_validate(gl)


def test_internship_gets_internship_projects():
    t = titles(load("swe_intern"))
    assert any("hackathon" in x.lower() for x in t)
    assert any("portfolio" in x.lower() for x in t)


def test_mid_skips_beginner_templates():
    gl = load("swe_mid")
    plan = build_plan(gl, TODAY)
    beginner = {pid for pid, p in catalog.projects().items() if "mid" not in p.get("levels", ["mid"])}
    assert not {s.project_id for s in plan.steps} & beginner
    assert any("Mentor" in s.title for s in plan.steps)


def test_same_gap_differs_by_level():
    entry, mid = load("swe_new_grad"), load("swe_new_grad")
    mid.target_role.level = "mid"
    assert titles(entry) != titles(mid), "level should change the plan for a full-stack gap"


def test_experience_gaps_dont_default_to_security():
    # A bare "experience" alias used to send every experience gap to a SOC lab.
    t = titles(load("it_career_changer"))
    assert not any("SOC" in x for x in t)


def test_unsupported_role_still_plans_with_a_warning():
    gl = load("swe_new_grad").model_dump(mode="json")
    gl["target_role"] = {"title": "Pastry Chef", "level": "entry"}
    r = generate.generate_roadmap(gl, TODAY, model=fake_model(exc=RuntimeError("offline")))
    assert r.target_role.role is None and r.steps
    assert any("isn't one of the roles" in w for w in r.warnings)


def test_senior_is_accepted_with_a_warning():
    gl = load("swe_mid")
    gl.target_role.level = "senior"
    r = generate.generate_roadmap(gl, TODAY, model=fake_model(exc=RuntimeError("offline")))
    assert r.steps and any("senior" in w for w in r.warnings)


# ---------- generate: personalization chain ----------

def fake_model(output: str = "", exc: Exception = None):
    calls = []

    def model(messages, _max_new_tokens):
        calls.append(messages)
        if exc:
            raise exc
        return output
    model.calls = calls
    return model


GOOD_TIPS = ("S1: Start with the array and hashing problems since you already know Java from class.\n"
             "SUMMARY: You have a solid CS base; this plan turns it into interview-ready proof.")


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(generate, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(generate, "DEMO_DIR", tmp_path / "demo")
    monkeypatch.delenv("ROADMAP_DEMO", raising=False)
    monkeypatch.delenv("ROADMAP_AI", raising=False)


def test_model_failure_falls_back_to_basic():
    r = generate.generate_roadmap(load("swe_new_grad"), TODAY, model=fake_model(exc=RuntimeError("boom")))
    assert r.source == "basic" and r.label == "Basic roadmap" and r.steps


def test_bad_tips_fall_back_to_basic():
    bad = "S1: See https://cheat.example.com, it works 100% of the time for everyone.\nS99: nonsense step here"
    r = generate.generate_roadmap(load("swe_new_grad"), TODAY, model=fake_model(bad))
    assert r.source == "basic" and all(s.tip is None for s in r.steps)


def test_good_tips_are_used_then_cached():
    gl = load("swe_new_grad")
    model = fake_model(GOOD_TIPS)
    first = generate.generate_roadmap(gl, TODAY, model=model)
    second = generate.generate_roadmap(gl, TODAY, model=model)
    assert first.source == "ai" and first.steps[0].tip and second.source == "cache"
    assert len(model.calls) == 1


def test_cache_is_per_day():
    gl = load("swe_new_grad")
    model = fake_model(GOOD_TIPS)
    generate.generate_roadmap(gl, TODAY, model=model)
    later = generate.generate_roadmap(gl, date(2026, 12, 1), model=model)
    assert later.source == "ai" and len(model.calls) == 2


def test_demo_mode_uses_saved_and_never_calls_model(monkeypatch):
    gl = load("swe_new_grad")
    saved = generate.generate_roadmap(gl, TODAY, model=fake_model(GOOD_TIPS))
    generate._save(generate.DEMO_DIR, generate.cache_key(gl), saved)
    monkeypatch.setenv("ROADMAP_DEMO", "1")
    model = fake_model(exc=AssertionError("demo mode must not call the model"))
    r = generate.generate_roadmap(gl, TODAY, model=model)
    assert r.source == "demo" and not model.calls


def test_busy_model_fails_fast_instead_of_queueing(monkeypatch):
    monkeypatch.setattr(local_model, "_slots", threading.BoundedSemaphore(1))
    local_model._slots.acquire()  # another user's request holds the only worker
    model = fake_model(GOOD_TIPS)
    with pytest.raises(local_model.ModelBusy):
        local_model.generate_with_timeout(model, [], timeout_s=5)
    r = generate.generate_roadmap(load("swe_new_grad"), TODAY, model=model)
    assert r.source == "basic" and not model.calls


def test_invalid_input_raises():
    with pytest.raises(Exception):
        generate.generate_roadmap({"gaps": "nope"}, TODAY)
