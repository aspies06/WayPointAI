"""Story bank persistence, ownership and the interview-to-resume workflow."""
import sqlite3

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


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WAYPOINT_STORY_DB", str(tmp_path / "stories.sqlite3"))
    monkeypatch.setenv("ROADMAP_AI", "0")
    monkeypatch.setenv("RESUME_AI", "0")
    with TestClient(api.app) as client:
        yield client


def library(client):
    response = client.post("/api/resume/library")
    assert response.status_code in (200, 201), response.text
    return {"Authorization": "Bearer " + response.json()["library_key"]}


def save(client, headers, story=None):
    response = client.post("/api/resume/stories", headers=headers, json=story or STORY)
    assert response.status_code in (200, 201), response.text
    return response.json()


def test_short_interview_and_preview_does_not_save(client):
    questions = client.get("/api/resume/questions").json()["questions"]
    assert [q["id"] for q in questions] == ["context", "problem", "actions", "tools", "outcome"]
    assert not next(q for q in questions if q["id"] == "outcome")["required"]
    headers = library(client)
    preview = client.post("/api/resume/stories/preview", headers=headers, json=STORY)
    assert preview.status_code == 200, preview.text
    assert "Python" in preview.json()["narrative"]
    assert "30 minutes" in preview.json()["narrative"]
    assert client.get("/api/resume/stories", headers=headers).json()["stories"] == []


def test_stories_survive_new_clients_and_can_be_edited_and_deleted(client):
    headers = library(client)
    saved = save(client, headers)
    with TestClient(api.app) as returning:
        records = returning.get("/api/resume/stories", headers=headers).json()["stories"]
        assert len(records) == 1 and records[0]["id"] == saved["id"]
        assert records[0]["answers"] == STORY["answers"]
        updated = {**STORY, "answers": {**STORY["answers"], "outcome": "Saved the team 2 hours each week."}}
        response = returning.put(f"/api/resume/stories/{saved['id']}", headers=headers, json=updated)
        assert response.status_code == 200, response.text
        assert "2 hours" in response.json()["narrative"]
        assert "30 minutes" not in response.json()["narrative"]
        removed = returning.delete(f"/api/resume/stories/{saved['id']}", headers=headers)
        assert removed.status_code in (200, 204)
        assert returning.get("/api/resume/stories", headers=headers).json()["stories"] == []


def test_other_libraries_cannot_read_change_delete_or_generate_from_a_story(client):
    owner, stranger = library(client), library(client)
    saved = save(client, owner)
    assert client.get("/api/resume/stories", headers=stranger).json()["stories"] == []
    path = f"/api/resume/stories/{saved['id']}"
    assert client.put(path, headers=stranger, json=STORY).status_code == 404
    assert client.delete(path, headers=stranger).status_code == 404
    assert client.post("/api/resume/generate", headers=stranger, json={}).status_code == 400
    assert len(client.get("/api/resume/stories", headers=owner).json()["stories"]) == 1


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer incorrect"}])
def test_story_access_needs_valid_library_key(client, headers):
    assert client.get("/api/resume/stories", headers=headers).status_code == 401
    assert client.post("/api/resume/stories", headers=headers, json=STORY).status_code == 401
    assert client.post("/api/resume/generate", headers=headers, json={}).status_code == 401


def test_database_does_not_contain_raw_library_key(client):
    headers = library(client)
    save(client, headers)
    import os
    with sqlite3.connect(os.environ["WAYPOINT_STORY_DB"]) as connection:
        dump = "\n".join(connection.iterdump())
    assert headers["Authorization"].split()[1] not in dump


def test_private_responses_are_not_cached_even_when_access_is_denied(client):
    headers = library(client)
    for response in (
        client.get("/api/resume/stories", headers=headers),
        client.get("/api/resume/stories"),
        client.post("/api/resume/library"),
    ):
        assert response.headers["cache-control"] == "no-store"


def test_unavailable_storage_returns_a_readable_error(client, tmp_path, monkeypatch):
    # A directory at the database location is an operational failure, not user input.
    monkeypatch.setenv("WAYPOINT_STORY_DB", str(tmp_path))
    response = client.post("/api/resume/library")
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize("field,value", [("context", "   "), ("actions", ""), ("problem", "x" * 20000)])
def test_invalid_facts_rejected_without_persistence(client, field, value):
    headers = library(client)
    body = {**STORY, "answers": {**STORY["answers"], field: value}}
    response = client.post("/api/resume/stories", headers=headers, json=body)
    assert response.status_code == 400, response.text
    assert client.get("/api/resume/stories", headers=headers).json()["stories"] == []


def test_resume_uses_saved_facts_with_sources_and_reports_missing_terms(client):
    headers = library(client)
    saved = save(client, headers)
    response = client.post("/api/resume/generate", headers=headers, json={
        "job_description": "Build Python and SQL reporting pipelines. Kubernetes experience required.",
        "profile": {"name": "Taylor Example", "education": "B.S. Computer Science"},
    })
    assert response.status_code == 200, response.text
    resume = response.json()
    assert resume["mode"] == "basic"
    assert resume["sections"][0]["story_id"] == saved["id"]
    assert "Taylor Example" in resume["text"] and "B.S. Computer Science" in resume["text"]
    assert "Kubernetes" not in resume["text"]
    assert "kubernetes" in {term.lower() for term in resume["unmatched_terms"]}
    for section in resume["sections"]:
        for bullet in section["bullets"]:
            assert bullet["evidence"]
            for evidence in bullet["evidence"]:
                assert evidence["quote"] in saved["answers"][evidence["field"]]


def test_unmeasured_experience_generates_without_fabricating_metrics(client):
    headers = library(client)
    save(client, headers, {**STORY, "answers": {**STORY["answers"], "tools": "", "outcome": ""}, "dates": ""})
    response = client.post("/api/resume/generate", headers=headers, json={})
    assert response.status_code == 200, response.text
    text = response.json()["text"]
    assert "Python" in text
    assert not any(c.isdigit() for c in text)


def test_story_mutations_work_from_allowed_web_origin(client):
    for method in ("PUT", "DELETE"):
        response = client.options("/api/resume/stories/example", headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5500"
