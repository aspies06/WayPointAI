"""Build data/role_insights.json: what people in each role do, from O*NET.

    python scripts/build_role_insights.py                  # reads ~/waypoint-data
    python scripts/build_role_insights.py --data /path/to/waypoint-data

Source: O*NET 31.0 (U.S. Department of Labor, CC BY 4.0). For the closest occupation to
each role: its most important tasks, as rated by people who hold the job, and the
technologies O*NET flags as In Demand (often listed in employer job postings for the
occupation) or Hot. Task text and technology names are quoted with attribution.

No scraped job-board data is used. The raw O*NET download stays outside the repo
(~/waypoint-data/onet); only this summary is committed.
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROLES = ["Software Engineer", "AI/ML Engineer", "Data Scientist", "Security Engineer",
         "Computer Engineer", "IT Support Specialist", "Hardware Engineer", "QA Engineer",
         "Product Manager"]

# O*NET has no exact match for some roles; say so instead of implying precision.
ONET_MATCH = {
    "Software Engineer": ("15-1252.00", "close"),
    "AI/ML Engineer": ("15-1221.00", "approximate"),     # Computer and Information Research Scientists
    "Data Scientist": ("15-2051.00", "close"),
    "Security Engineer": ("15-1299.05", "close"),        # Information Security Engineers
    "Computer Engineer": ("17-2061.00", "approximate"),  # Computer Hardware Engineers
    "IT Support Specialist": ("15-1232.00", "close"),    # Computer User Support Specialists
    "Hardware Engineer": ("17-2072.00", "approximate"),  # Electronics Engineers, Except Computer
    "QA Engineer": ("15-1253.00", "close"),
    "Product Manager": ("15-1299.09", "approximate"),    # Information Technology Project Managers
}

TOP_TASKS, TOP_TECH = 8, 20


def tsv(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f, delimiter="\t")


def onet_insights(onet_dir: Path) -> dict:
    wanted = {code for code, _ in ONET_MATCH.values()}
    titles = {r["O*NET-SOC Code"]: r["Title"] for r in tsv(onet_dir / "Occupation Data.txt")
              if r["O*NET-SOC Code"] in wanted}
    importance = {}
    for r in tsv(onet_dir / "Task Ratings.txt"):
        if r["O*NET-SOC Code"] in wanted and r["Scale ID"] == "IM":
            importance[(r["O*NET-SOC Code"], r["Task ID"])] = float(r["Data Value"])
    tasks = defaultdict(list)
    for r in tsv(onet_dir / "Task Statements.txt"):
        code = r["O*NET-SOC Code"]
        if code in wanted:
            tasks[code].append({"task": r["Task"], "type": r["Task Type"],
                                "importance": importance.get((code, r["Task ID"])),
                                "source": r["Domain Source"]})
    tech = defaultdict(list)
    for r in tsv(onet_dir / "Software Skills.txt"):
        code = r["O*NET-SOC Code"]
        if code in wanted and (r["In Demand"] == "Y" or r["Hot Technology"] == "Y"):
            tech[code].append({"name": r["Workplace Example"], "category": r["Element Name"],
                               "in_demand": r["In Demand"] == "Y", "hot": r["Hot Technology"] == "Y"})
    out = {}
    for role, (code, match) in ONET_MATCH.items():
        ranked = sorted(tasks[code], key=lambda t: (t["type"] != "Core", -(t["importance"] or 0)))
        ranked_tech = sorted(tech[code], key=lambda t: (not t["in_demand"], not t["hot"], t["name"].lower()))
        out[role] = {
            "code": code, "title": titles.get(code, ""), "match": match,
            "tasks": [{"task": t["task"], "importance": t["importance"], "source": t["source"]}
                      for t in ranked[:TOP_TASKS]],
            "technologies": ranked_tech[:TOP_TECH],
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path.home() / "waypoint-data")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "role_insights.json")
    args = ap.parse_args()
    onet = onet_insights(args.data / "onet" / "db_31_0_text")
    result = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "onet": {
                "name": "O*NET 31.0 Database (August 2026)",
                "publisher": "U.S. Department of Labor, Employment and Training Administration",
                "url": "https://www.onetcenter.org/database.html",
                "license": "CC BY 4.0",
                "attribution": ("This includes information from the O*NET 31.0 Database by the U.S. Department of "
                                "Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 "
                                "license. O*NET® is a trademark of USDOL/ETA."),
                "note": "Task importance comes from surveys of people who work in each occupation.",
            },
        },
        "roles": {role: {"onet": onet[role]} for role in ROLES},
    }
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    for role in ROLES:
        o = onet[role]
        print(f"{role:22} {o['code']} {o['title'][:40]:40} ({o['match']}) tasks={len(o['tasks'])} "
              f"in_demand={sum(t['in_demand'] for t in o['technologies'])} tech={len(o['technologies'])}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
