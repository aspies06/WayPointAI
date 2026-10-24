"""The API behind the React front end (api.py)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402

LIVE_SERVER = "http://127.0.0.1:5500"
TIME = {"hours_per_week": "steady", "target_date": "05-31-2027", "start_date": "11-02-2026"}


@pytest.fixture(autouse=True)
def no_model(monkeypatch):
    monkeypatch.setenv("ROADMAP_AI", "0")


@pytest.fixture
def client():
    return TestClient(api.app)


def post(client, files=None, **fields):
    data = {"roles": ["Data Scientist"], **TIME, **fields}
    return client.post("/api/roadmaps", data=data, files=files)


def test_options_drive_the_form(client):
    body = client.get("/api/options").json()
    assert len(body["roles"]) == 9 and body["date_format"] == "MM-DD-YYYY"
    assert {w["value"] for w in body["workloads"]} >= {"light", "steady"}
    assert any(q["id"] == "target_date" and q["required"] for q in body["questions"])


def test_roadmap_from_typed_skills(client):
    res = post(client, skills_text="Python, SQL")
    assert res.status_code == 200, res.text
    body = res.json()
    result = body["results"][0]
    assert not body["starting_from_scratch"] and result["role"] == "Data Scientist"
    roadmap = result["roadmap"]
    assert roadmap["steps"] and roadmap["start_date"] == "2026-11-02" and roadmap["target_date"] == "2027-05-31"
    assert all(s["resources"] for s in roadmap["steps"] if s["resource_ids"])  # links resolved
    assert set(result["gap_names"]) == {g for s in roadmap["steps"] for g in s["gap_ids"]} | \
        {g for s in roadmap["optional"] for g in s["gap_ids"]} | {d["gap_id"] for d in roadmap["deferred"]}


def test_nothing_given_means_starting_from_scratch(client):
    body = post(client).json()
    assert body["starting_from_scratch"] and body["results"][0]["roadmap"]["steps"]


def test_resume_upload(client):
    res = post(client, files={"resume": ("resume.txt", b"Skills: Python, Pandas, SQL", "text/plain")})
    assert res.status_code == 200 and not res.json()["starting_from_scratch"]


def test_bad_resume_is_a_readable_error(client):
    res = post(client, files={"resume": ("resume.docx", b"...", "application/octet-stream")})
    assert res.status_code == 400 and "PDF or UTF-8 text" in res.json()["detail"]


def test_one_roadmap_per_role(client):
    res = post(client, roles=["Data Scientist", "QA Engineer", "Data Scientist"])
    assert [r["role"] for r in res.json()["results"]] == ["Data Scientist", "QA Engineer"]


@pytest.mark.parametrize("fields, message", [
    ({"target_date": ""}, "Please answer"),
    ({"target_date": "31-05-2027"}, "MM-DD-YYYY"),
    ({"hours_per_week": "lots"}, "number of hours"),
    ({"budget_usd": "a lot"}, "dollar amount"),
    ({"roles": ["Astronaut"]}, "listed roles"),
    ({"level": "wizard"}, "experience level"),
    ({"roles": []}, "listed roles"),
    ({"experience_years": "-3"}, "Please check: experience years"),
])
def test_bad_answers_get_a_clear_message(client, fields, message):
    res = post(client, **fields)
    assert res.status_code == 400 and message in res.json()["detail"], res.text


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5173", "http://localhost:5173",
                                    "http://127.0.0.1:4173", LIVE_SERVER])
def test_the_site_may_call_it(client, origin):
    res = client.get("/api/health", headers={"Origin": origin})
    assert res.headers.get("access-control-allow-origin") == origin


def test_other_sites_may_not(client):
    res = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in res.headers
