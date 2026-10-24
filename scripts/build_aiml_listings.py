"""Build data/aiml_listings.json: which skills junior and mid-level ML engineer job listings ask for.

    python scripts/build_aiml_listings.py

O*NET has no Machine Learning Engineer occupation (its closest are Data Scientists and
Computer and Information Research Scientists), so the AI/ML Engineer role's skills come from
job listings instead. Source: the AI Dev Jobs public API (https://aidevboard.com/docs), found
through the CC0 list emredurukn/awesome-job-boards. Its terms (https://aidevboard.com/terms,
April 16, 2026) allow data from the API to be "used in your applications but ... not resold
as a standalone dataset", and say listing content belongs to the hiring companies. So only
tag counts and shares are saved: no listing text, titles, companies or links.

Only listings whose title names a machine learning or AI engineering role are counted, and
tags that name an industry (healthcare, payments, ...) rather than a skill are dropped.
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

API = "https://aidevboard.com/api/v1/jobs"
LEVELS = ("junior", "mid")
QUERIES = ("machine learning engineer", "ml engineer", "ai engineer")
MAX_PAGES = 6  # per query and level; 50 listings a page, well inside the hourly limit

# "Machine Learning Engineer", "ML Engineer II", "Applied AI Engineer", "Software Engineer, Machine Learning"
TITLE = re.compile(r"\b(machine learning|ml|ai|mlops|deep learning|computer vision|nlp|llm)\b.*\bengineer"
                   r"|\bengineer\b.*\b(machine learning|ml|ai|mlops|deep learning|computer vision|nlp|llm)\b", re.I)
NOT_ENGINEERING = re.compile(r"\b(manager|director|recruit|sales|account|curriculum|designer|scientist)\b", re.I)

# Tags that describe the employer's industry or the job's setting, not something to learn.
NOT_SKILLS = {"healthcare", "payments", "fintech", "finance", "robotics", "autonomous-vehicles", "research",
              "education", "gaming", "biotech", "climate", "defense", "ecommerce", "legal", "insurance",
              "security", "crypto", "web3", "media", "adtech", "hardware", "startup", "enterprise", "remote"}


def fetch(query: str, level: str, page: int) -> dict:
    url = f"{API}?{urllib.parse.urlencode({'q': query, 'level': level, 'limit': 50, 'page': page})}"
    request = urllib.request.Request(url, headers={"User-Agent": "WayPointAI student project (role skills summary)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect(level: str) -> list[dict]:
    seen: dict[str, dict] = {}
    for query in QUERIES:
        for page in range(1, MAX_PAGES + 1):
            data = fetch(query, level, page)
            for job in data.get("jobs", []):
                title = job.get("title") or ""
                if TITLE.search(title) and not NOT_ENGINEERING.search(title):
                    seen[str(job["id"])] = job
            if not data.get("has_next"):
                break
            time.sleep(0.5)
    return list(seen.values())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "aiml_listings.json")
    args = ap.parse_args()

    jobs = {level: collect(level) for level in LEVELS}
    unique = {str(j["id"]): j for level in LEVELS for j in jobs[level]}
    counts = Counter(tag for job in unique.values() for tag in set(job.get("tags") or []) if tag not in NOT_SKILLS)
    total = len(unique)
    out = {
        "_note": "Share of junior and mid-level ML/AI engineer job listings tagged with each skill. "
                 "Built by scripts/build_aiml_listings.py; only counts are stored.",
        "source": {
            "name": "AI Dev Jobs public API",
            "url": "https://aidevboard.com",
            "terms": "https://aidevboard.com/terms",
            "found_via": "https://github.com/emredurukn/awesome-job-boards (CC0)",
            "attribution": "AI/ML Engineer skills: share of junior and mid-level ML engineer job listings on "
                           "AI Dev Jobs (aidevboard.com) tagged with each skill, collected "
                           f"{datetime.now(timezone.utc):%B %Y}.",
        },
        "collected": datetime.now(timezone.utc).date().isoformat(),
        "listings": {"total": total, **{level: len(jobs[level]) for level in LEVELS}},
        "skills": [{"tag": tag, "listings": n, "share": round(n / total, 3)}
                   for tag, n in counts.most_common() if n >= 3],
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{total} listings ({', '.join(f'{lvl} {len(jobs[lvl])}' for lvl in LEVELS)}); top skills:")
    for s in out["skills"][:25]:
        print(f"  {s['tag']:<24} {s['share']:.0%}")


if __name__ == "__main__":
    main()
