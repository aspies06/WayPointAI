# Gap list format (v1.0)

The backend sends this to the roadmap module. The roadmap module sends a roadmap back.
Source of truth: `roadmap/schemas.py`. Samples for every level are in `tests/personas/`
(`swe_intern.json`, `swe_new_grad.json`, `swe_mid.json`, ...).

The app is built for **internship, junior (entry) and mid-level** roles. Senior is accepted, but it is
planned with mid-level resources and the roadmap carries a warning.

Supported roles (`target_role.role`):

`Software Engineer`, `AI/ML Engineer`, `Data Scientist`, `Security Engineer`, `Computer Engineer`,
`IT Support Specialist`, `Hardware Engineer`, `QA Engineer`, `Product Manager`

Send `role` when you know it. If it's left out, it's inferred from `title` ("Data Science Intern" →
Data Scientist, "SDET" → QA Engineer). Any other title still gets a plan from the general resources,
with a warning that more gaps may be deferred.

## Gap list (backend → roadmap)

```json
{
  "schema_version": "1.0",
  "target_role": {"title": "Software Engineering Intern", "level": "internship", "role": "Software Engineer"},
  "gaps": [
    {
      "gap_id": "g1",
      "item": "Data structures and algorithms practice",
      "category": "skill",
      "peer_share": 80,
      "severity": "high",
      "user_has": "Intro DSA class in progress"
    }
  ],
  "user_context": {
    "hours_per_week": 10,
    "target_date": "2027-01-31",
    "budget_usd": 0,
    "background": "Second-year CS student; Python and Java from classes."
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `target_role.title` | string, ≤120 chars | The job title as shown to the user, e.g. "Data Science Intern". |
| `target_role.role` | one of the 9 roles above, or omitted | Case-insensitive. Inferred from `title` if omitted; `null` in the output if no role matched. Project templates are filtered by role. |
| `target_role.level` | `internship` \| `entry` \| `mid` \| `senior` | Case-insensitive. Aliases: `intern` → internship; `junior`, `new grad`, `entry-level` → entry; `mid-level`, `intermediate` → mid. Project templates are filtered by level. |
| `gap_id` | string, ≤40 chars | Unique within the list. The roadmap refers to gaps by this ID. |
| `item` | string, ≤120 chars | Short name of the missing thing: "Security+", "React", "Active Directory". Matched against the resource catalog, so plain names work best. |
| `category` | `cert` \| `skill` \| `tool` \| `experience` \| `education` | |
| `peer_share` | integer 0–100 | Percent of people in the role who have it. |
| `severity` | `high` \| `medium` \| `low` | Suggested rule: high if peer_share ≥ 60 or the job post requires it, medium if 30–59, low otherwise. |
| `user_has` | string or null, ≤200 chars | What the user has instead, if anything. |
| `hours_per_week` | integer 1–80 | |
| `target_date` | `YYYY-MM-DD` | |
| `budget_usd` | integer ≥ 0 | |
| `background` | string, ≤600 chars | One or two lines. |

Max 40 gaps. Unknown fields are rejected, so typos fail loudly instead of being silently ignored.

## Roadmap (roadmap → UI)

```json
{
  "schema_version": "1.0",
  "target_role": {"title": "Software Engineering Intern", "level": "internship", "role": "Software Engineer"},
  "source": "ai",
  "label": "Personalized roadmap",
  "summary": "...",
  "total_hours": 60,
  "available_hours": 140,
  "warnings": [],
  "steps": [
    {
      "step_id": "S1",
      "title": "Solve a structured set of coding problems",
      "phase": "first_30_days",
      "type": "project",
      "gap_ids": ["g1"],
      "why": "80% of Software Engineering Intern hires have Data structures and algorithms practice (high priority).",
      "deliverable": "...",
      "done_when": "...",
      "resource_ids": ["R-NEETCODE"],
      "project_id": "P-DSA-PRACTICE",
      "est_hours": 60,
      "depends_on": [],
      "tip": "Start with arrays and hashing; your Java class covers the syntax you need."
    }
  ],
  "deferred": [{"gap_id": "g7", "reason": "..."}]
}
```

- `source`: `ai`, `cache`, `demo` or `basic`. Show `label` ("Personalized roadmap" or "Basic roadmap") as a small tag. Never show raw errors.
- `tip`: optional personal advice from the local model; may be null on any step.
- `warnings`: short user-facing notes (over budget, senior level, unsupported role).
- `phase`: `first_30_days`, `days_30_90` or `days_90_plus`. Group steps by phase.
- `resource_ids`: look these up in `data/catalog.json` for name, link, cost and hours.
- Every input gap appears in at least one step's `gap_ids` or in `deferred`.

## Calling it

```python
from roadmap import generate_roadmap
roadmap = generate_roadmap(gap_list_dict)   # returns a Roadmap; .model_dump() for JSON
```

Or from the command line: `python -m roadmap tests/personas/swe_intern.json`.
