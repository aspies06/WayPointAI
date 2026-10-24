"""Role insights (O*NET) and how the resume builder uses them."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api
import role_insights
from roadmap.schemas import ROLES

ROOT = Path(__file__).resolve().parent.parent

IT_STORY = {
    "answers": {
        "context": "Student help desk assistant",
        "problem": "New staff couldn't sign in on their first day.",
        "actions": "Reset passwords and unlocked accounts in Active Directory, and walked staff through Windows setup.",
        "tools": "Active Directory, Windows",
        "outcome": "Staff were signed in before their first meeting.",
    },
    "organization": "Campus IT", "dates": "2025",
}
OTHER_STORY = {
    "answers": {
        "context": "Café shift lead",
        "problem": "Weekend lines were long.",
        "actions": "Reorganized the order station.",
        "tools": "", "outcome": "",
    },
    "organization": "", "dates": "",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WAYPOINT_STORY_DB", str(tmp_path / "stories.sqlite3"))
    monkeypatch.setenv("ROADMAP_AI", "0")
    monkeypatch.setenv("RESUME_AI", "0")
    with TestClient(api.app) as client:
        yield client


def bank(client, *stories):
    headers = {"Authorization": "Bearer " + client.post("/api/resume/library").json()["library_key"]}
    for story in stories:
        assert client.post("/api/resume/stories", headers=headers, json=story).status_code == 201
    return headers


# ---------- the data file ----------

def test_data_covers_every_role_from_onet_with_attribution():
    data = json.loads((ROOT / "data" / "role_insights.json").read_text())
    assert list(data["roles"]) == list(ROLES)
    assert data["sources"]["onet"]["license"] == "CC BY 4.0" and "USDOL/ETA" in data["sources"]["onet"]["attribution"]
    for role, entry in data["roles"].items():
        assert entry["onet"]["tasks"] and entry["onet"]["match"] in ("close", "approximate"), role


def test_no_job_board_data():
    text = (ROOT / "data" / "role_insights.json").read_text().lower()
    data = json.loads(text)
    assert set(data["sources"]) == {"onet"}
    assert all(set(entry) == {"onet"} for entry in data["roles"].values())
    for word in ("linkedin", "kaggle", "asaniczka", "simplyhired", "postings"):
        assert word not in text, word


# ---------- the loader ----------

def test_only_in_demand_technologies_are_shown():
    raw = role_insights._data()["roles"]["IT Support Specialist"]["onet"]["technologies"]
    shown = role_insights.for_role("IT Support Specialist")["in_demand_technologies"]
    assert [t["name"] for t in shown] == [t["name"] for t in raw if t["in_demand"]]


@pytest.mark.parametrize("name, short", [
    ("Microsoft Active Directory", "Active Directory"),
    ("Structured query language SQL", "SQL"),
    ("Amazon Web Services AWS software", "AWS"),
    ("Microsoft Azure software", "Azure"),
    ("Jenkins CI", "Jenkins"),
    ("Microsoft Power BI", "Power BI"),
])
def test_everyday_names_match(name, short):
    assert short in role_insights.match_terms(name)


def test_vendor_stays_in_long_names():
    assert "Web Services" not in role_insights.match_terms("Amazon Web Services AWS software")


def test_unknown_role():
    assert role_insights.for_role("Astronaut") is None


# ---------- API and resume builder ----------

def test_insights_endpoint_is_public_and_cited(client):
    res = client.get("/api/resume/insights", params={"role": "Data Scientist"})
    assert res.status_code == 200
    body = res.json()
    assert body["people_in_role"]["tasks"] and body["in_demand_technologies"]
    assert len(body["sources"]) == 1 and "O*NET" in body["sources"][0]
    assert client.get("/api/resume/insights", params={"role": "Astronaut"}).status_code == 400


def test_role_ranks_relevant_stories_first_and_reports_coverage(client):
    headers = bank(client, IT_STORY, OTHER_STORY)  # newest first, so the café story starts on top
    res = client.post("/api/resume/generate", headers=headers,
                      json={"role": "IT Support Specialist", "max_stories": 1})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["sections"][0]["context"].lower().startswith("student help desk")
    found = {t["name"]: t["in_your_stories"] for t in body["role_insights"]["in_demand_technologies"]}
    assert found["Microsoft Active Directory"] is True and found["Microsoft Windows"] is True
    assert found["ServiceNow"] is False
    assert body["unmatched_terms"] == []  # with no job description, role technologies aren't listed as gaps


def test_role_never_adds_claims(client):
    headers = bank(client, OTHER_STORY)
    body = client.post("/api/resume/generate", headers=headers, json={"role": "IT Support Specialist"}).json()
    for tech in ("Active Directory", "ServiceNow", "Windows"):
        assert tech not in body["text"]


def test_unknown_role_is_rejected(client):
    headers = bank(client, IT_STORY)
    assert client.post("/api/resume/generate", headers=headers, json={"role": "Astronaut"}).status_code == 400


def test_level_is_no_longer_a_field(client):
    headers = bank(client, IT_STORY)
    res = client.post("/api/resume/generate", headers=headers, json={"role": "IT Support Specialist", "level": "entry"})
    assert res.status_code in (400, 422)  # extra fields are rejected


def test_delete_story_bank_erases_everything(client):
    headers = bank(client, IT_STORY, OTHER_STORY)
    assert client.delete("/api/resume/library", headers=headers).json() == {"deleted": True}
    assert client.get("/api/resume/stories", headers=headers).status_code == 401
