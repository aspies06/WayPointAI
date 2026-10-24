"""Gap analysis endpoints in api.py: GET /api/roles and POST /api/analyze (Component 3)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402
from role_profiles import ROLE_PROFILES  # noqa: E402

# ---------- sample resumes and requests (paste any into /docs to try it) ----------

STRONG_DS_RESUME = {
    "skills": ["Python", "SQL", "Machine Learning", "Pandas", "Scikit-learn"],
    "education": [{"degree": "BSc", "field": "Statistics"}],
    "experience_years": 2.5,
    "projects": ["Built a churn prediction model", "Created a sales forecasting dashboard"],
}
WEAK_DS_RESUME = {
    "skills": ["Python", "Excel", "Tableau"],
    "education": [{"degree": "BSc", "field": "Economics"}],
    "experience_years": 1.5,
    "projects": ["Built a sales dashboard"],
}
SWE_RESUME = {
    "skills": ["Python", "Git", "REST APIs", "Docker"],
    "education": [{"degree": "BSc", "field": "Computer Science"}],
    "experience_years": 1.0,
    "projects": ["Open-source CLI tool", "REST API for a student project"],
}
NO_SKILLS_RESUME = {
    "skills": [],
    "education": [{"degree": "BA", "field": "History"}],
    "experience_years": 0.0,
    "projects": [],
}
EMPTY_RESUME = {"skills": [], "experience_years": 0.0}

REQUESTS = {
    "data_scientist_strong": {"resume": STRONG_DS_RESUME, "role": "Data Scientist"},
    "data_scientist_weak": {"resume": WEAK_DS_RESUME, "role": "Data Scientist"},
    "software_engineer_partial": {"resume": SWE_RESUME, "role": "Software Engineer"},
    "career_changer_no_skills": {"resume": NO_SKILLS_RESUME, "role": "Software Engineer"},
}

CUSTOM_ROLE = {  # not in ROLE_PROFILES, to test the role_profile path
    "resume": WEAK_DS_RESUME,
    "role_profile": {
        "role": "Analytics Engineer",
        "required_skills": [
            {"skill": "SQL", "frequency": 0.95},
            {"skill": "dbt", "frequency": 0.88},
            {"skill": "Python", "frequency": 0.75},
        ],
        "preferred_skills": [
            {"skill": "Tableau", "frequency": 0.40},
            {"skill": "Spark", "frequency": 0.35},
        ],
        "avg_years_experience": 2.0,
        "common_education": ["Computer Science", "Statistics"],
    },
}


@pytest.fixture
def client():
    return TestClient(api.app)


def analyze(client, payload):
    return client.post("/api/analyze", json=payload)


# ---------- GET /api/roles ----------

def test_roles_returns_all_roles(client):
    resp = client.get("/api/roles")
    assert resp.status_code == 200
    assert {r["role"] for r in resp.json()["roles"]} == set(ROLE_PROFILES)


def test_roles_profile_shape(client):
    for role in client.get("/api/roles").json()["roles"]:
        assert {"role", "required_skills", "preferred_skills", "avg_years_experience"} <= role.keys()
        assert isinstance(role["required_skills"], list)
        for entry in role["required_skills"]:
            assert {"skill", "frequency"} <= entry.keys()


# ---------- POST /api/analyze, by role name ----------

@pytest.mark.parametrize("payload", REQUESTS.values(), ids=REQUESTS.keys())
def test_analyze_role_name(client, payload):
    resp = analyze(client, payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert 0 <= data["match_score"] <= 100
    assert isinstance(data["skills_present"], list)
    assert isinstance(data["experience_gap"], (float, int)) and data["experience_gap"] >= 0
    assert isinstance(data["weak_areas"], list)
    for s in data["skills_missing"]:
        assert {"skill", "priority", "frequency"} <= s.keys()


def test_more_matching_skills_score_higher(client):
    strong = analyze(client, REQUESTS["data_scientist_strong"]).json()["match_score"]
    weak = analyze(client, REQUESTS["data_scientist_weak"]).json()["match_score"]
    assert strong > weak


def test_no_skills_scores_zero(client):
    resp = analyze(client, {"resume": EMPTY_RESUME, "role": "Data Scientist"})
    assert resp.status_code == 200
    assert resp.json()["match_score"] == 0


# ---------- POST /api/analyze, with a full role profile ----------

def test_custom_role_profile(client):
    resp = analyze(client, CUSTOM_ROLE)
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["match_score"] <= 100
    assert "python" in [s.lower() for s in data["skills_present"]]


def test_role_profile_wins_over_role_name(client):
    resp = analyze(client, {**CUSTOM_ROLE, "role": "Data Scientist"})
    assert resp.status_code == 200
    missing = [s["skill"] for s in resp.json()["skills_missing"]]
    assert any(s in missing for s in ["SQL", "dbt"])


# ---------- errors (api.py turns validation errors into a plain 400) ----------

def test_needs_role_or_profile(client):
    assert analyze(client, {"resume": {"skills": ["Python"], "experience_years": 1.0}}).status_code == 400


def test_unknown_role(client):
    resp = analyze(client, {"resume": {"skills": ["Python"], "experience_years": 1.0}, "role": "Astronaut"})
    assert resp.status_code == 404
    assert "Astronaut" in resp.json()["detail"]


def test_missing_resume(client):
    resp = analyze(client, {"role": "Data Scientist"})
    assert resp.status_code == 400
    assert "resume" in resp.json()["detail"]


def test_frequency_out_of_range(client):
    resp = analyze(client, {
        "resume": {"skills": ["Python"], "experience_years": 1.0},
        "role_profile": {"role": "Test Role", "avg_years_experience": 1.0,
                         "required_skills": [{"skill": "Python", "frequency": 1.5}]},
    })
    assert resp.status_code == 400


# ---------- ordering ----------

def test_missing_skills_by_priority_then_frequency(client):
    resp = analyze(client, {"resume": EMPTY_RESUME, "role": "Data Scientist"})
    assert resp.status_code == 200
    missing = resp.json()["skills_missing"]
    assert [s["priority"] for s in missing] == sorted(s["priority"] for s in missing)
    freqs = [s["frequency"] for s in missing]
    assert freqs == sorted(freqs, reverse=True)
