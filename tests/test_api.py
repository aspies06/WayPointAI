"""
tests/test_api.py
-----------------
Integration tests for the FastAPI layer (Component 3, Person B).

Run:
    pytest tests/test_api.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.mock_data import MOCK_REQUESTS, MOCK_ROLE
from role_profiles import ROLE_PROFILES

client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /roles
# ---------------------------------------------------------------------------


def test_roles_returns_all_roles():
    resp = client.get("/roles")
    assert resp.status_code == 200
    data = resp.json()
    assert "roles" in data
    returned_names = {r["role"] for r in data["roles"]}
    assert returned_names == set(ROLE_PROFILES.keys())


def test_roles_profile_shape():
    resp = client.get("/roles")
    for role in resp.json()["roles"]:
        assert "role" in role
        assert "required_skills" in role
        assert "preferred_skills" in role
        assert "avg_years_experience" in role
        assert isinstance(role["required_skills"], list)
        for skill_entry in role["required_skills"]:
            assert "skill" in skill_entry
            assert "frequency" in skill_entry


# ---------------------------------------------------------------------------
# POST /analyze — happy paths via role name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", MOCK_REQUESTS, ids=[f["_name"] for f in MOCK_REQUESTS])
def test_analyze_role_name(fixture):
    payload = {k: v for k, v in fixture.items() if not k.startswith("_")}
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "match_score" in data
    assert 0 <= data["match_score"] <= 100
    assert isinstance(data["skills_present"], list)
    assert isinstance(data["skills_missing"], list)
    assert isinstance(data["experience_gap"], (float, int))
    assert data["experience_gap"] >= 0
    assert isinstance(data["weak_areas"], list)

    for s in data["skills_missing"]:
        assert "skill" in s
        assert "priority" in s
        assert "frequency" in s


def test_analyze_score_improves_with_more_skills():
    """A resume with more matching skills should score higher."""
    strong_resp = client.post("/analyze", json={"resume": MOCK_REQUESTS[0]["resume"], "role": "Data Scientist"})
    weak_resp = client.post("/analyze", json={"resume": MOCK_REQUESTS[1]["resume"], "role": "Data Scientist"})
    assert strong_resp.json()["match_score"] > weak_resp.json()["match_score"]


def test_analyze_no_skills_scores_zero():
    """A resume with no skills should score 0."""
    payload = {
        "resume": {"skills": [], "experience_years": 0.0},
        "role": "Data Scientist",
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    assert resp.json()["match_score"] == 0


# ---------------------------------------------------------------------------
# POST /analyze — custom role_profile path
# ---------------------------------------------------------------------------


def test_analyze_custom_role_profile():
    resp = client.post("/analyze", json=MOCK_ROLE)
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["match_score"] <= 100
    # Candidate has Python and Tableau, missing SQL and dbt
    present = [s.lower() for s in data["skills_present"]]
    assert "python" in present


def test_analyze_role_profile_takes_precedence():
    """When both role and role_profile are given, role_profile wins."""
    payload = {**MOCK_ROLE, "role": "Data Scientist"}
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 200
    # The custom role has 3 required + 2 preferred skills, not the DS profile
    # so skills_missing should reference SQL / dbt, not DS-specific skills
    missing_names = [s["skill"] for s in resp.json()["skills_missing"]]
    assert any(s in missing_names for s in ["SQL", "dbt"])


# ---------------------------------------------------------------------------
# POST /analyze — error cases
# ---------------------------------------------------------------------------


def test_analyze_missing_both_role_and_profile():
    payload = {"resume": {"skills": ["Python"], "experience_years": 1.0}}
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 400


def test_analyze_unknown_role():
    payload = {"resume": {"skills": ["Python"], "experience_years": 1.0}, "role": "Astronaut"}
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 404
    assert "Astronaut" in resp.json()["detail"]


def test_analyze_missing_resume():
    resp = client.post("/analyze", json={"role": "Data Scientist"})
    assert resp.status_code == 422  # Pydantic validation error


def test_analyze_invalid_frequency():
    """Frequencies outside 0–1 should be rejected by Pydantic."""
    payload = {
        "resume": {"skills": ["Python"], "experience_years": 1.0},
        "role_profile": {
            "role": "Test Role",
            "required_skills": [{"skill": "Python", "frequency": 1.5}],  # invalid
            "avg_years_experience": 1.0,
        },
    }
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Priority ordering
# ---------------------------------------------------------------------------


def test_missing_skills_sorted_by_priority():
    resp = client.post("/analyze", json={"resume": {"skills": [], "experience_years": 0.0}, "role": "Data Scientist"})
    assert resp.status_code == 200
    missing = resp.json()["skills_missing"]
    priorities = [s["priority"] for s in missing]
    assert priorities == sorted(priorities)


def test_missing_skills_sorted_by_frequency_desc():
    resp = client.post("/analyze", json={"resume": {"skills": [], "experience_years": 0.0}, "role": "Data Scientist"})
    missing = resp.json()["skills_missing"]
    freqs = [s["frequency"] for s in missing]
    assert freqs == sorted(freqs, reverse=True)
