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

## Step 1: ask about the user's time

A roadmap only helps if it fits the person's real time, so **ask before you plan**. The questions are in
`roadmap/intake.py` (`QUESTIONS`): how many hours a week they can sustain (light, steady, intensive,
full time or a number), when they can start, when they want to be ready, and their budget.

```python
from roadmap import intake
for q in intake.QUESTIONS: ...                     # render as form fields: id, prompt, help, options, required
ctx = intake.answers_to_context(form_answers, background="...")   # ValueError with a user-readable message if invalid
gap_list["user_context"] = ctx.model_dump(mode="json")
```

If `user_context` is missing, `generate_roadmap()` raises `intake.AvailabilityNeeded`, whose `.questions`
lists what to ask. It never guesses.

## Step 2: gap list (backend → roadmap)

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
    "budget_usd": 150,
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
| `user_context` | object, or omitted | Omitted means "not asked yet": `generate_roadmap()` raises `AvailabilityNeeded`. |
| `hours_per_week` | integer 1–80 | The workload the user said they can sustain. |
| `start_date` | `YYYY-MM-DD` in JSON, optional | When they can start; today if omitted. The timeline begins here. |
| `target_date` | `YYYY-MM-DD` in JSON | Must be after `start_date`. |

People **enter** dates as **MM-DD-YYYY** (`intake.DATE_FORMAT`; `05-31-2027` or `5/31/2027`); `answers_to_context()` converts them. JSON between programs stays ISO `YYYY-MM-DD`.
| `budget_usd` | integer ≥ 0, or omitted/`null` | What the user chose to spend, including 0. Omitted or `null` means no limit. Nothing is assumed. |
| `background` | string, ≤600 chars | One or two lines. |

Max 40 gaps. Unknown fields are rejected, so typos fail loudly instead of being silently ignored.

## Step 3: roadmap (roadmap → UI)

**Only the timeline is shown up front. Everything else sits behind an optional button.** In Streamlit,
`roadmap.ui` does both parts: `availability_form()` asks the questions (dates as MM-DD-YYYY), and
`show_roadmap()` shows the timeline plus a "Show optional items (N)" button. For another UI, use
`render.timeline_markdown()` for the main view, `render.optional_markdown()` behind your button, and
`render.optional_count()` for the button label. The timeline is a table, then steps grouped
**Must do → Should do → Nice to have**, each with its
dates, deliverable, source links and any "Worth considering" notes.

```json
{
  "schema_version": "1.0",
  "target_role": {"title": "Software Engineering Intern", "level": "internship", "role": "Software Engineer"},
  "source": "ai",
  "label": "Personalized roadmap",
  "summary": "...",
  "total_hours": 60,
  "available_hours": 140,
  "hours_per_week": 10,
  "start_date": "2026-10-23",
  "finish_date": "2026-12-04",
  "target_date": "2027-01-31",
  "warnings": [],
  "steps": [
    {
      "step_id": "S1",
      "title": "Solve a structured set of coding problems",
      "priority": "must_do",
      "phase": "first_30_days",
      "type": "project",
      "gap_ids": ["g1"],
      "why": "80% of Software Engineering Intern hires have Data structures and algorithms practice (high priority).",
      "deliverable": "...",
      "done_when": "...",
      "resource_ids": ["R-NEETCODE"],
      "project_id": "P-DSA-PRACTICE",
      "est_hours": 60,
      "cost_usd": 0,
      "depends_on": [],
      "tip": "Start with arrays and hashing; your Java class covers the syntax you need.",
      "start_date": "2026-10-23",
      "end_date": "2026-12-04",
      "resources": [{"id": "R-NEETCODE", "name": "NeetCode 150 roadmap", "provider": "NeetCode",
                     "url": "https://neetcode.io/", "cost_usd": 0, "type": "lab"}]
    }
  ],
  "deferred": [{"gap_id": "g8", "reason": "Costs about $390, which goes over your $150 budget. It's listed as optional item O2."}],
  "optional": [{"step_id": "O1", "title": "Pass CompTIA A+ (Core 1 + Core 2 exams)", "optional_because": "budget",
                "cost_usd": 510, "start_date": null, "...": "same fields as steps"}]
}
```

- `source`: `ai`, `cache`, `demo` or `basic`. Show `label` ("Personalized roadmap" or "Basic roadmap") as a small tag. Never show raw errors.
- `tip`: optional personal advice from the local model; may be null on any step.
- `warnings`: short user-facing notes (over budget, senior level, unsupported role).
- `phase`: `first_30_days`, `days_30_90` or `days_90_plus`. Group steps by phase.
- `priority`: `must_do`, `should_do` or `nice_to_have`, from the most severe gap the step closes. Steps come in this order.
- `start_date` / `end_date`: the step's dates, one step at a time at the user's `hours_per_week`, from `start_date`. `finish_date` is when the last step ends, so compare it with `target_date`. Over-budget options have no dates.
- `resources`: the `resource_ids` resolved to name, provider, link and cost. Links only come from `data/catalog.json`, which was link-checked on 2026-10-23.
- Every input gap appears in at least one step's `gap_ids` or in `deferred`.
- `cost_usd` on a step is the new spending it needs. A resource that an earlier step already bought counts as $0. Timeline steps add up to no more than `budget_usd`.
- `benefit`: what finishing the step earns: `certification` (a real exam), `certificate` (a certificate of completion the provider issues), `portfolio` (a project you can show), or `knowledge` (no certificate exists, so the value is the skill itself). Show it as a label.
- `shortened_from` / `scope_note`: when must-do work doesn't fit, big steps are cut to fit (title ends "(part 1)") and keep their place at the front. `shortened_from` is the full hours, and the rest is an optional item ending "(part 2)". `scope_note` explains this, or why a cert step became exam prep. Show it when present.
- `suggestions`: "Worth considering" notes, at most two per step, each with `kind` (`credential`, `cheaper` or `faster`), `reason` and a `resource` link. They may go over the budget on purpose.
- `optional`: everything that isn't on the user's timeline, for the UI to show behind a button. Each item is a full step (deliverable, links, cost, hours) with no dates, IDs `O1`, `O2`, ... `optional_because` is `time` (doesn't fit, or the part 2 of a shortened step) or `budget` (over what the user chose to spend, including an exam whose prep is on the timeline). Gaps that are only in optional items are also in `deferred`, with a reason naming the item. Gaps with nothing in the catalog appear only in `deferred`, and the optional section lists them as "Not covered yet".

## Calling it

```python
from roadmap import generate_roadmap
roadmap = generate_roadmap(gap_list_dict)   # returns a Roadmap; .model_dump() for JSON
```

Or from the command line: `python -m roadmap tests/personas/swe_intern.json`. This prints the readable
response, and it asks the availability questions first if the file has no `user_context` (or always, with
`--ask`). Add `--json` for the raw Roadmap.
