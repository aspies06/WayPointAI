"""The interview-to-resume workflow. The server stores nothing: stories come with each request."""
import pytest
from fastapi.testclient import TestClient

import api


STORY = {
    "answers": {
        "context": "Software engineering intern",
        "problem": "Support staff copied weekly reports by hand.",
        "actions": "Built a Python script to validate records and export reports.",
        "tools": "Python, SQL, Git",
        "outcome": "Reduced report preparation from 3 hours to 30 minutes.",
    },
    "organization": "Campus help desk",
    "dates": "June–August 2025",
}
SAVED = {**STORY, "id": "s1", "narrative": "Software engineering intern.", "created_at": "", "updated_at": ""}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WAYPOINT_STORY_DB", str(tmp_path / "stories.sqlite3"))
    monkeypatch.setenv("ROADMAP_AI", "0")
    monkeypatch.setenv("RESUME_AI", "0")
    with TestClient(api.app) as client:
        yield client


def test_short_interview_and_preview(client):
    questions = client.get("/api/resume/questions").json()["questions"]
    assert [q["id"] for q in questions] == ["context", "problem", "actions", "tools", "outcome"]
    assert not next(q for q in questions if q["id"] == "outcome")["required"]
    preview = client.post("/api/resume/stories/preview", json=STORY)
    assert preview.status_code == 200, preview.text
    assert "Python" in preview.json()["narrative"]
    assert "30 minutes" in preview.json()["narrative"]


def test_server_keeps_no_story_storage(client, tmp_path):
    client.post("/api/resume/stories/preview", json=STORY)
    client.post("/api/resume/generate", json={"stories": [SAVED]})
    assert not (tmp_path / "stories.sqlite3").exists()
    for path in ("/api/resume/library", "/api/resume/stories"):
        assert client.post(path, json=STORY).status_code in (404, 405)
    assert client.get("/api/resume/stories").status_code in (404, 405)


def test_generate_needs_stories(client):
    assert client.post("/api/resume/generate", json={}).status_code == 400
    assert client.post("/api/resume/generate", json={"stories": []}).status_code == 400
    assert client.post("/api/resume/generate", json={"stories": [SAVED, SAVED]}).status_code == 400  # duplicate ids
    too_many = [{**SAVED, "id": f"s{i}"} for i in range(51)]
    assert client.post("/api/resume/generate", json={"stories": too_many}).status_code == 400


def test_responses_are_not_cached(client):
    for response in (client.post("/api/resume/stories/preview", json=STORY),
                     client.post("/api/resume/generate", json={"stories": [SAVED]})):
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("field,value", [("context", "   "), ("actions", ""), ("problem", "x" * 20000)])
def test_invalid_facts_rejected(client, field, value):
    body = {**STORY, "answers": {**STORY["answers"], field: value}}
    assert client.post("/api/resume/stories/preview", json=body).status_code == 400
    assert client.post("/api/resume/generate", json={"stories": [{**SAVED, **body}]}).status_code == 400


def test_resume_uses_sent_facts_with_sources_and_reports_missing_terms(client):
    response = client.post("/api/resume/generate", json={
        "stories": [SAVED],
        "job_description": "Build Python and SQL reporting pipelines. Kubernetes experience required.",
        "profile": {"name": "Taylor Example", "education": "B.S. Computer Science"},
    })
    assert response.status_code == 200, response.text
    resume = response.json()
    assert resume["mode"] == "basic"
    assert resume["sections"][0]["story_id"] == "s1"
    assert "Taylor Example" in resume["text"] and "B.S. Computer Science" in resume["text"]
    assert "Kubernetes" not in resume["text"]
    assert "kubernetes" in {term.lower() for term in resume["unmatched_terms"]}
    for section in resume["sections"]:
        for bullet in section["bullets"]:
            assert bullet["evidence"]
            for evidence in bullet["evidence"]:
                assert evidence["quote"] in STORY["answers"][evidence["field"]]


def test_unmeasured_experience_generates_without_fabricating_metrics(client):
    story = {**SAVED, "answers": {**STORY["answers"], "tools": "", "outcome": ""}, "dates": ""}
    response = client.post("/api/resume/generate", json={"stories": [story]})
    assert response.status_code == 200, response.text
    text = response.json()["text"]
    assert "Python" in text
    assert not any(c.isdigit() for c in text)


def test_resume_calls_work_from_allowed_web_origin(client):
    response = client.options("/api/resume/generate", headers={
        "Origin": "http://127.0.0.1:5500",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5500"
