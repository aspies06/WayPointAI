"""What people in each role do, from O*NET.

Reads data/role_insights.json, built by scripts/build_role_insights.py from O*NET 31.0
(U.S. Department of Labor, CC BY 4.0): the tasks rated most important by people who hold
the closest occupation, and the technologies O*NET flags as In Demand (often listed in
employer job postings for that occupation). AI/ML Engineer, which O*NET doesn't track, uses
the share of junior and mid-level ML engineer listings asking for each skill (AI Dev Jobs API;
see scripts/build_aiml_listings.py). Nothing is scraped.
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

DATA = Path(__file__).resolve().parent.parent / "data" / "role_insights.json"
LISTINGS = Path(__file__).resolve().parent.parent / "data" / "aiml_listings.json"

# O*NET has no Machine Learning Engineer occupation, so this role's skills come from job listings
# (scripts/build_aiml_listings.py). Listing tags name topics, not languages or libraries, so a few
# core tools come from O*NET: Python, SQL and Git (in demand for research scientists, data
# scientists and software developers alike) and scikit-learn and pandas (research and data
# scientists). Cloud comes from the listings' own tag.
LISTING_ROLE = "AI/ML Engineer"
MIN_LISTING_SHARE = 0.10
# tag -> (name a resume would use, other ways people write it)
LISTING_SKILLS = {
    "llm": ("Large language models (LLMs)", ["LLM", "LLMs", "large language model"]),
    "machine-learning": ("Machine learning", ["machine learning", "ML"]),
    "pytorch": ("PyTorch", ["PyTorch"]),
    "agents": ("AI agents", ["AI agent", "agentic", "LLM agent"]),
    "fine-tuning": ("Fine-tuning models", ["fine-tuning", "fine tuning", "finetuning", "LoRA"]),
    "generative-ai": ("Generative AI", ["generative AI", "GenAI"]),
    "deep-learning": ("Deep learning", ["deep learning", "neural network"]),
    "distributed-systems": ("Distributed systems", ["distributed systems", "distributed training"]),
    "data-pipeline": ("Data pipelines", ["data pipeline", "ETL"]),
    "gpu": ("GPU computing", ["GPU", "CUDA"]),
    "tensorflow": ("TensorFlow", ["TensorFlow", "Keras"]),
    "mlops": ("MLOps", ["MLOps", "model deployment"]),
    "reinforcement-learning": ("Reinforcement learning", ["reinforcement learning"]),
    "computer-vision": ("Computer vision", ["computer vision", "OpenCV"]),
    "cloud": ("Cloud platforms", ["AWS", "Azure", "GCP", "Google Cloud", "cloud"]),
}
CORE_TOOLS = ["Python", "Structured query language SQL", "Git", "Scikit-learn", "pandas"]
QUALIFIERS = {"CI"}
VENDORS = ("The MathWorks", "Microsoft", "Apple", "Atlassian", "Amazon", "Google", "IBM", "Oracle", "Adobe", "Apache")


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _listings() -> Optional[dict]:
    return json.loads(LISTINGS.read_text(encoding="utf-8")) if LISTINGS.exists() else None


def listing_skills() -> list[dict]:
    """AI/ML Engineer skills from job listings: {"name", "share", "terms"}, most asked-for first.
    Vague tags (platform, search, infrastructure) aren't in LISTING_SKILLS and are left out."""
    data = _listings()
    if not data:
        return []
    return [{"name": LISTING_SKILLS[s["tag"]][0], "share": s["share"],
             "terms": [LISTING_SKILLS[s["tag"]][0], *LISTING_SKILLS[s["tag"]][1]]}
            for s in data["skills"] if s["tag"] in LISTING_SKILLS and s["share"] >= MIN_LISTING_SHARE]


def listing_source() -> Optional[str]:
    data = _listings()
    return data["source"]["attribution"] if data else None


def roles() -> list[str]:
    return list(_data()["roles"])


def match_terms(name: str) -> list[str]:
    """Names people actually write for an O*NET technology: "Microsoft Active Directory" ->
    "Active Directory", "Structured query language SQL" -> "SQL", "Amazon Web Services AWS
    software" -> "AWS". The full name is always included."""
    terms = [name]
    base = re.sub(r"\s+software$", "", name)
    words = base.split()
    if len(words) > 1 and re.fullmatch(r"[A-Z][A-Z0-9]{2,}", words[-1]):
        # Trailing acronym: "Amazon Web Services AWS" -> "AWS" and "Amazon Web Services".
        # The vendor stays in the long form, so "Web Services" alone never matches.
        terms += [words[-1], " ".join(words[:-1])]
    else:
        if len(words) > 1 and words[-1] in QUALIFIERS:  # "Jenkins CI" -> "Jenkins"; "Power BI" stays
            base = " ".join(words[:-1])
        for vendor in VENDORS:
            if base.startswith(vendor + " "):
                base = base[len(vendor) + 1:]
                break
        terms.append(base)
    seen, out = set(), []
    for term in terms:
        if term and term.casefold() not in seen:
            seen.add(term.casefold())
            out.append(term)
    return out


def for_role(role: str, n_tasks: int = 6) -> Optional[dict]:
    """Insights for one role, or None for an unknown role."""
    data = _data()
    entry = data["roles"].get(role)
    if entry is None:
        return None
    onet = entry["onet"]
    if role == LISTING_ROLE and listing_skills():
        return _listing_view(role, onet, data)
    return {
        "role": role,
        "people_in_role": {
            "occupation": onet["title"],
            "onet_code": onet["code"],
            "match": onet["match"],
            "tasks": [t["task"] for t in onet["tasks"][:n_tasks]],
        },
        # O*NET's own employer-demand signal for the occupation; "Hot" is across all jobs, so it's left out.
        "in_demand_technologies": [{"name": t["name"], "terms": match_terms(t["name"])}
                                   for t in onet["technologies"] if t["in_demand"]],
        "sources": [data["sources"]["onet"]["attribution"]],
    }


def _listing_view(role: str, onet: dict, data: dict) -> dict:
    """AI/ML Engineer: O*NET's tasks belong to research scientists, so the panel shows what
    junior and mid-level ML engineer listings ask for, plus O*NET's core tools."""
    found = {t["name"] for t in onet["technologies"]}
    core = [{"name": name, "terms": match_terms(name)} for name in CORE_TOOLS if name in found]
    return {
        "role": role,
        "people_in_role": {
            "occupation": "machine learning engineers",
            "onet_code": onet["code"],
            "match": "listings",
            "tasks": [],
            "note": "O*NET doesn't track machine learning engineers as their own job, so the skills here "
                    "come from junior and mid-level ML engineer job listings instead.",
        },
        "in_demand_technologies": [{"name": s["name"], "terms": s["terms"]} for s in listing_skills()] + core,
        "technologies_note": "Skills most often asked for in junior and mid-level ML engineer job listings, "
                             "then core tools O*NET flags as in demand for related jobs.",
        "sources": [listing_source(), data["sources"]["onet"]["attribution"]],
    }
