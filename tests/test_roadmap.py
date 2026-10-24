"""Offline tests: no model download or network needed."""
import threading
from datetime import date
from pathlib import Path
import pytest

from roadmap import GapList, catalog, generate, intake, local_model
from roadmap.guardrails import check
from roadmap.planner import build_plan
from roadmap import render
from roadmap.render import to_markdown
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


def test_no_budget_given_means_no_limit():
    gl = load("twenty_gaps")
    gl.user_context.budget_usd = None
    plan = build_plan(gl, TODAY)
    assert not [s for s in plan.optional if s.optional_because == "budget"]
    assert check(plan, gl, TODAY) == ([], [])


def test_user_sets_any_budget_including_zero():
    gl = load("it_intern")
    gl.user_context.budget_usd = 0
    plan = build_plan(gl, TODAY)
    assert plan.steps and sum(s.cost_usd for s in plan.steps) == 0


def test_cert_over_budget_becomes_free_prep_plus_a_nudge():
    gl = load("it_intern")  # $150 budget; CompTIA A+ costs about $510
    plan = build_plan(gl, TODAY)
    prep = next(s for s in plan.steps if s.title == "Prepare for CompTIA A+ (Core 1 + Core 2 exams)")
    assert prep.cost_usd == 0 and "R-APLUS" not in prep.resource_ids
    nudge = next(x for x in prep.suggestions if x.kind == "credential")
    assert nudge.resource_id == "R-APLUS" and "over your budget" in nudge.reason
    exam = next(s for s in plan.optional if s.resource_ids == ["R-APLUS"])
    assert exam.optional_because == "budget" and exam.cost_usd == 510
    assert sum(s.cost_usd for s in plan.steps) <= gl.user_context.budget_usd


def test_paid_steps_point_out_free_alternatives():
    from roadmap.planner import _suggestions
    gl = load("data_scientist_intern")
    gap = gl.gaps[4]  # "Machine learning basics"
    paid = good_step(type="course", benefit="certificate", gap_ids=[gap.gap_id],
                     resource_ids=["R-ML-SPEC"], est_hours=60, cost_usd=49)
    tips = _suggestions(paid, gap, gl.target_role, budget_left=0)
    cheaper = next(x for x in tips if x.kind == "cheaper")
    assert catalog.resources()[cheaper.resource_id]["cost_usd"] == 0 and "saves about $49" in cheaper.reason


def test_bad_optional_item_is_caught():
    gl = load("swe_new_grad")
    draft = draft_for(gl, [good_step()])
    draft.optional = [good_step(step_id="O1", resource_ids=["R-MADE-UP"])]
    errors, _ = check(draft, gl, TODAY)
    assert any("O1" in e and "not in the catalog" in e for e in errors)


def test_steps_that_dont_fit_the_time_stay_available_as_optional():
    gl = load("impossible_deadline")  # 5 h/week for four weeks
    plan = build_plan(gl, TODAY)
    late = [s for s in plan.optional if s.optional_because == "time"]
    assert late and all(s.start_date is None and s.resource_ids for s in late)
    assert sum(s.est_hours for s in plan.steps) <= guardrails_hours(gl)
    kept = {g for s in plan.optional for g in s.gap_ids}
    assert all(d.gap_id in kept or d.reason.startswith("No curated") for d in plan.deferred)


def guardrails_hours(gl):
    from roadmap.guardrails import available_hours
    return available_hours(gl, TODAY)


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

    def model(messages, *_):
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
    monkeypatch.setattr(generate, "CACHE_DIR", None)
    generate.clear_cache()
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


def test_cache_stays_in_memory_by_default():
    generate.generate_roadmap(load("swe_new_grad"), TODAY, model=fake_model(GOOD_TIPS))
    assert generate.CACHE_DIR is None and generate._memory
    assert not (Path(generate.ROOT) / "cache").exists() or not any((Path(generate.ROOT) / "cache").iterdir())


def test_disk_cache_is_owner_only_and_expires(tmp_path, monkeypatch):
    import os
    import time
    monkeypatch.setattr(generate, "CACHE_DIR", tmp_path / "cache")
    generate.generate_roadmap(load("swe_new_grad"), TODAY, model=fake_model(GOOD_TIPS))
    files = list((tmp_path / "cache").glob("*.json"))
    assert files and all(f.stat().st_mode & 0o077 == 0 for f in files)  # no group/other access
    old = time.time() - generate.CACHE_TTL_S - 60
    os.utime(files[0], (old, old))
    generate._purge_expired(tmp_path / "cache")
    assert not files[0].exists()


def test_cache_keys_differ_for_different_people():
    a, b = load("swe_new_grad"), load("swe_new_grad")
    b.user_context.background += " Different person."
    assert generate.cache_key(a) != generate.cache_key(b) and len(generate.cache_key(a)) == 64


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


# ---------- ask first: availability and workload ----------

def test_no_availability_means_ask_not_guess():
    gl = load("swe_intern").model_dump(mode="json")
    del gl["user_context"]
    with pytest.raises(intake.AvailabilityNeeded) as e:
        generate.generate_roadmap(gl, TODAY)
    assert {"hours_per_week", "target_date"} <= {q["id"] for q in e.value.questions}


@pytest.mark.parametrize("answers, hours, target", [
    ({"hours_per_week": "steady", "target_date": "12"}, 8, date(2027, 1, 15)),
    ({"hours_per_week": "6h", "target_date": "03-01-2027", "start_date": "11-01-2026"}, 6, date(2027, 3, 1)),
    ({"hours_per_week": "10", "target_date": "3/1/2027"}, 10, date(2027, 3, 1)),
    ({"hours_per_week": "10", "target_date": date(2027, 3, 1)}, 10, date(2027, 3, 1)),  # st.date_input
    ({"hours_per_week": " Light ", "target_date": "4 weeks", "budget_usd": "$75"}, 4, date(2026, 11, 20)),
])
def test_answers_become_context(answers, hours, target):
    ctx = intake.answers_to_context(answers, today=TODAY)
    assert (ctx.hours_per_week, ctx.target_date) == (hours, target)
    assert ctx.budget_usd == (75 if "budget_usd" in answers else None)  # blank = no limit


@pytest.mark.parametrize("answers", [
    {"target_date": "12"},                                   # workload missing
    {"hours_per_week": "lots", "target_date": "12"},
    {"hours_per_week": "200", "target_date": "12"},
    {"hours_per_week": "8", "target_date": "someday"},
    {"hours_per_week": "8", "start_date": "02-01-2027", "target_date": "01-01-2027"},
    {"hours_per_week": "8", "target_date": "31-05-2027"},   # day first is not MM-DD-YYYY
])
def test_bad_answers_are_rejected(answers):
    with pytest.raises(ValueError):
        intake.answers_to_context(answers, today=TODAY)


def test_cli_reasks_until_answers_are_valid():
    replies = iter(["a lot", "", "steady", "", "yesterday", "8", ""])  # 3 bad answers, then good ones
    shown = []
    ctx = intake.ask_cli(input_fn=lambda _: next(replies), print_fn=shown.append)
    assert ctx.hours_per_week == 8 and ctx.budget_usd is None
    assert sum("Try again" in m or "needed" in m for m in shown) == 3


# ---------- response: priority, timeline, sources ----------

# ---------- big priorities first, shortened rather than dropped ----------

@pytest.mark.parametrize("path", PERSONAS, ids=lambda p: p.stem)
def test_lower_priorities_never_take_time_from_higher_ones(path):
    gl = GapList.model_validate_json(path.read_text())
    plan = build_plan(gl, TODAY)
    rank = {"must_do": 0, "should_do": 1, "nice_to_have": 2}
    on = [rank[s.priority] for s in plan.steps]
    assert on == sorted(on), "timeline must run in priority order"
    waiting = [rank[s.priority] for s in plan.optional if s.optional_because == "time"]
    if waiting and on:
        assert max(on) <= min(waiting), "a lower tier is scheduled while a higher one waits"


def test_big_must_dos_are_shortened_and_kept_at_the_top():
    gl = load("impossible_deadline")  # 20 hours available; coding practice alone is 60
    plan = build_plan(gl, TODAY)
    first = plan.steps[0]
    assert first.priority == "must_do" and first.shortened_from == 60 and first.est_hours < 60
    assert "(part 1)" in first.title and "Part 1 of" in first.deliverable
    part2 = next(s for s in plan.optional if s.title.endswith("(part 2)") and s.gap_ids == first.gap_ids)
    assert first.est_hours + part2.est_hours == 60
    assert all(s.priority == "must_do" for s in plan.steps)
    assert sum(s.est_hours for s in plan.steps) <= guardrails_hours(gl)


def test_steps_that_fit_are_never_shortened():
    plan = build_plan(load("swe_new_grad"), TODAY)  # plenty of time
    assert not any(s.shortened_from for s in plan.steps)


# ---------- certifications are real; everything else is labeled honestly ----------

def test_only_real_exams_are_certifications():
    for r in catalog.resources().values():
        assert (r["type"] == "cert") == (r.get("credential") == "certification"), r["id"]
        assert r.get("credential") in (None, "certificate", "certification"), r["id"]


@pytest.mark.parametrize("path", PERSONAS, ids=lambda p: p.stem)
def test_steps_only_promise_credentials_that_exist(path):
    gl = GapList.model_validate_json(path.read_text())
    plan = build_plan(gl, TODAY)
    for s in [*plan.steps, *plan.optional]:
        creds = {catalog.resources()[r].get("credential") for r in s.resource_ids}
        promised = f"{s.deliverable} {s.done_when}".lower()
        if s.benefit == "certification":
            assert "certification" in creds, s.title
        if s.benefit == "certificate":
            assert "certificate" in creds, s.title
        if s.benefit == "knowledge":
            assert "certificate" not in promised and "no certificate" in s.why.lower() or s.title.startswith("Prepare"), s.title


def test_cert_gap_without_an_exam_is_offered_as_knowledge():
    gl = load("swe_new_grad")
    gl.gaps[0].category, gl.gaps[0].item = "cert", "Docker"  # no Docker certification in the catalog
    step = next(s for s in build_plan(gl, TODAY).steps if gl.gaps[0].gap_id in s.gap_ids)
    assert step.benefit != "certification" and "No certification" in step.why


def test_steps_come_in_priority_order_with_a_timeline():
    gl = load("product_manager_entry")
    r = generate.generate_roadmap(gl, TODAY, model=fake_model(exc=RuntimeError("offline")))
    order = {"must_do": 0, "should_do": 1, "nice_to_have": 2}
    assert [order[s.priority] for s in r.steps] == sorted(order[s.priority] for s in r.steps)
    assert r.steps[0].start_date == TODAY and r.finish_date == r.steps[-1].end_date
    for a, b in zip(r.steps, r.steps[1:]):
        assert a.start_date <= a.end_date <= b.start_date  # one thing at a time, no overlaps
    hours = sum(s.est_hours for s in r.steps)
    assert (r.finish_date - TODAY).days == pytest.approx(hours * 7 / gl.user_context.hours_per_week, abs=len(r.steps))


def test_timeline_starts_when_the_user_can():
    gl = load("swe_intern")
    gl.user_context.start_date = date(2026, 12, 1)
    assert build_plan(gl, TODAY).steps[0].start_date == date(2026, 12, 1)


def test_every_step_links_its_sources_from_the_catalog():
    r = generate.generate_roadmap(load("it_intern"), TODAY, model=fake_model(exc=RuntimeError("offline")))
    for s in [*r.steps, *r.optional]:
        assert [x.id for x in s.resources] == s.resource_ids
        assert all(x.url == catalog.resources()[x.id]["url"] for x in s.resources)


def test_timeline_and_optional_are_separate():
    gl = load("impossible_deadline")
    r = generate.generate_roadmap(gl, TODAY, model=fake_model(exc=RuntimeError("offline")))
    names = {g.gap_id: g.item for g in gl.gaps}
    timeline, extra = render.timeline_markdown(r, names), render.optional_markdown(r, names)
    assert all(s.title not in timeline for s in r.optional)
    assert all(s.title in extra for s in r.optional) and "If you get more time" in extra
    assert render.optional_count(r) == len(r.optional)  # every deferred gap here has an optional item


def test_ui_hides_optional_items_until_the_button_is_pressed():
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    at = AppTest.from_file(str(Path(__file__).parent.parent / "scripts" / "demo_app.py"), default_timeout=30)
    at.run()
    at.selectbox[0].set_value("impossible_deadline").run()
    assert not at.markdown or "Timeline" not in " ".join(m.value for m in at.markdown)  # asks first
    at.number_input[0].set_value(5)
    at.radio[0].set_value("custom")
    at.button[0].click().run()  # "Make my roadmap"
    text = lambda: " ".join(m.value for m in at.markdown)
    assert "Timeline" in text() and "If you get more time" not in text()
    show = next(b for b in at.button if b.label.startswith("Show optional"))
    show.click().run()
    assert "If you get more time" in text()
    assert any(b.label.startswith("Hide optional") for b in at.button)


def test_response_reads_in_priority_order():
    gl = load("data_scientist_intern")
    r = generate.generate_roadmap(gl, TODAY, model=fake_model(exc=RuntimeError("offline")))
    md = to_markdown(r, {g.gap_id: g.item for g in gl.gaps})
    assert md.index("### Must do") < md.index("### Should do") < md.index("### Nice to have")
    assert "### Timeline" in md and "](https://" in md


def test_invalid_input_raises():
    with pytest.raises(Exception):
        generate.generate_roadmap({"gaps": "nope"}, TODAY)


# ---------- compatibility with WayPointAI's gap analyzer (gap_analyzer.py, role_profiles.py) ----------

def test_slash_separated_skills_match_each_part():
    assert catalog.resources_for("VHDL/Verilog", "entry", "Hardware Engineer")
    assert catalog.resources_for("C/C++", "entry", "Computer Engineer")
    assert catalog.resources_for("CI/CD", "entry")  # aliases that contain a slash still match


def test_long_free_text_is_trimmed_not_rejected():
    gl = load("swe_new_grad").model_dump(mode="json")
    gl["gaps"][0]["user_has"] = "Has: " + ", ".join(f"skill {i}" for i in range(60))
    gl["user_context"]["background"] = "x" * 2000
    parsed = GapList.model_validate(gl)
    assert len(parsed.gaps[0].user_has) == 200 and parsed.gaps[0].user_has.endswith("…")
    assert len(parsed.user_context.background) == 600


def test_works_with_the_gap_analyzer_for_every_role():
    gap_analyzer = pytest.importorskip("gap_analyzer")  # runs once this lives in the WayPointAI repo
    profiles = pytest.importorskip("role_profiles").ROLE_PROFILES
    resume = {"skills": ["Python", "SQL", "Git"], "experience_years": 0.5}
    ctx = {"hours_per_week": 10, "target_date": "2027-06-01", "budget_usd": 200}
    for role, profile in profiles.items():
        gl = gap_analyzer.build_gap_list(gap_analyzer.analyze_gap(resume, profile),
                                         {"title": role, "level": "entry", "role": role}, ctx, resume)
        r = generate.generate_roadmap(gl, TODAY, model=fake_model(exc=RuntimeError("offline")))
        uncovered = [d for d in r.deferred if d.reason.startswith("No curated")]
        assert r.steps and len(uncovered) <= len(gl["gaps"]) / 4, (role, uncovered)


# ---------- honest numbers and wording ----------

@pytest.mark.parametrize("path", PERSONAS, ids=lambda p: p.stem)
def test_estimated_shares_are_said_in_words(path):
    gl = GapList.model_validate_json(path.read_text())  # personas use estimates, like role_profiles.py
    plan = build_plan(gl, TODAY)
    for s in [*plan.steps, *plan.optional]:
        assert "%" not in s.why, s.why
        assert s.why.split()[0] in ("Most", "Some", "Not"), s.why


def test_measured_shares_keep_their_percentage():
    gl = load("swe_new_grad")
    gl.peer_share_measured = True
    first = build_plan(gl, TODAY).steps[0]
    assert first.why.startswith(f"{gl.gaps[1].peer_share}% of")


@pytest.mark.parametrize("share, words", [(90, "Most"), (65, "Most"), (64, "Some"), (40, "Some"), (39, "Not many")])
def test_share_words_thresholds(share, words):
    from roadmap.planner import share_words
    assert share_words(share, measured=False) == words


def test_skills_no_hire_has_are_left_out():
    gl = load("swe_new_grad")
    gl.gaps[0].peer_share = 0
    plan = build_plan(gl, TODAY)
    gone = gl.gaps[0].gap_id
    assert gone not in {g for s in [*plan.steps, *plan.optional] for g in s.gap_ids}
    assert gone not in {d.gap_id for d in plan.deferred}
    assert check(plan, gl, TODAY)[0] == []


@pytest.mark.parametrize("years, text", [(1.0, "1 year"), (2.0, "2 years"), (1.5, "1.5 years"), (0.5, "0.5 years")])
def test_whole_years_have_no_decimal(years, text):
    from roadmap.planner import years_text
    assert years_text(years) == text


def _with_experience_gap(level, years="1"):
    gl = load("it_intern").model_dump(mode="json")
    gl["target_role"] = {"title": "IT Support Specialist", "level": level, "role": "IT Support Specialist"}
    gl["gaps"].append({"gap_id": "gx", "item": f"{years} more year of experience", "category": "experience",
                       "peer_share": 100, "severity": "high", "user_has": "0 years"})
    return GapList.model_validate(gl)


def test_work_experience_is_said_directly_not_scheduled():
    gl = _with_experience_gap("entry")
    plan = build_plan(gl, TODAY)
    assert plan.experience and plan.experience.gap_id == "gx" and plan.experience.years == 1
    msg = plan.experience.message
    assert "about 1 more year of work experience" in msg and "help desk" in msg
    assert "gx" not in {g for s in [*plan.steps, *plan.optional] for g in s.gap_ids}
    assert check(plan, gl, TODAY)[0] == []


def test_mid_level_experience_points_to_a_junior_job():
    plan = build_plan(_with_experience_gap("mid", "2"), TODAY)
    assert "about 2 more years of work experience" in plan.experience.message
    assert "a junior IT Support Specialist job" in plan.experience.message


def test_internships_dont_ask_for_experience():
    plan = build_plan(_with_experience_gap("internship"), TODAY)
    assert plan.experience.message.startswith("Internships don't expect work experience")


def test_experience_note_is_on_top_not_in_not_covered():
    r = generate.generate_roadmap(_with_experience_gap("entry"), TODAY, model=fake_model(exc=RuntimeError("offline")))
    md = render.to_markdown(r)
    assert md.index("Most important") < md.index("### Timeline")
    assert "gx" not in {d.gap_id for d in render._uncovered(r)}


def test_gap_analyzer_years_have_no_decimal():
    gap_analyzer = pytest.importorskip("gap_analyzer")
    profiles = pytest.importorskip("role_profiles").ROLE_PROFILES
    import re
    for years in (0, 0.5, 1):
        resume = {"skills": ["Python"], "experience_years": years}
        for role, profile in profiles.items():
            gl = gap_analyzer.build_gap_list(gap_analyzer.analyze_gap(resume, profile),
                                             {"title": role, "level": "entry", "role": role},
                                             {"hours_per_week": 8, "target_date": "2027-06-01"}, resume)
            r = generate.generate_roadmap(gl, TODAY, model=fake_model(exc=RuntimeError("offline")))
            text = render.to_markdown(r, {g["gap_id"]: g["item"] for g in gl["gaps"]})
            assert not re.search(r"\b\d+\.0\b", text), role
            assert not re.search(r"\b\d+% of [\w/ ]+ hires\b", text), role  # estimates are said in words


# ---------- local model: timeout and device choice ----------

def fake_torch(cuda_free=None, mps_free=None):
    """Stands in for torch: cuda_free / mps_free are free bytes, or None if that GPU is absent."""
    from types import SimpleNamespace as NS
    return NS(
        cuda=NS(is_available=lambda: cuda_free is not None, mem_get_info=lambda: (cuda_free, 24e9)),
        backends=NS(mps=NS(is_available=lambda: mps_free is not None)),
        mps=NS(recommended_max_memory=lambda: mps_free, driver_allocated_memory=lambda: 0),
    )


GB = 1_000_000_000


def test_timeout_defaults_to_two_minutes():
    import importlib
    import os
    if "ROADMAP_TIMEOUT_S" not in os.environ:
        assert importlib.reload(local_model).TIMEOUT_S == 120


@pytest.mark.parametrize("torch_, requested, device", [
    (fake_torch(), "auto", "cpu"),                       # no GPU at all
    (fake_torch(mps_free=8 * GB), "auto", "mps"),        # Apple GPU with room
    (fake_torch(cuda_free=8 * GB), "auto", "cuda"),      # NVIDIA GPU with room
    (fake_torch(cuda_free=1 * GB), "auto", "cpu"),       # not enough free GPU memory
    (fake_torch(mps_free=8 * GB), "cpu", "cpu"),         # user forced the CPU
    (fake_torch(mps_free=8 * GB), "cuda", "cpu"),        # asked for CUDA on a Mac
    (fake_torch(cuda_free=8 * GB), "cuda", "cuda"),
])
def test_device_choice(torch_, requested, device):
    chosen, reason = local_model.choose_device(torch_, weight_bytes=1 * GB, requested=requested)
    assert chosen == device and reason


def test_gpu_needs_room_for_more_than_the_weights():
    just_the_weights = fake_torch(cuda_free=1 * GB)
    assert local_model.choose_device(just_the_weights, 1 * GB, "auto")[0] == "cpu"
    assert local_model.choose_device(fake_torch(cuda_free=2 * GB), 1 * GB, "auto")[0] == "cuda"
