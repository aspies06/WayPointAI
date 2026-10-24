# Roadmap module

Takes a gap list (what a user is missing compared with people in the target role) and returns a concrete, scheduled roadmap. The plan is built from a curated catalog with plain rules, so it is grounded and never empty. A small local model then adds a personal tip per step, and every tip is checked in code.

Built for **internship, junior and mid-level** candidates in nine roles:

> Software Engineer · AI/ML Engineer · Data Scientist · Security Engineer · Computer Engineer · IT Support Specialist · Hardware Engineer · QA Engineer · Product Manager

Senior targets and other titles still get a plan, along with a warning.

- Input and output format: [docs/gap_list_spec.md](gap_list_spec.md)
- Entry point: `generate_roadmap(gap_list) -> Roadmap` in `roadmap/generate.py`

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                       # offline tests, no model needed
ROADMAP_AI=0 .venv/bin/python -m roadmap tests/personas/swe_intern.json
.venv/bin/pip install torch transformers            # optional: personal tips
```

## How it stays reliable

| Layer | When it's used | UI label |
|---|---|---|
| Demo mode (`ROADMAP_DEMO=1`) | Saved roadmaps from `demo/`, no model | Personalized roadmap |
| Cache | Same gap list already personalized today | Personalized roadmap |
| Local model (45s timeout) | Normal path; each tip must pass the line checks | Personalized roadmap |
| Basic roadmap | Model off, busy, slow, failed, or every tip rejected | Basic roadmap |

Guardrails (`roadmap/guardrails.py`) run on every roadmap. They fail it if:
- A step cites an unknown gap, or a resource or project that isn't in the catalog.
- The roadmap contains a URL. Links come only from `data/catalog.json`.
- A gap is neither covered nor deferred with a reason.
- A deliverable or `done_when` is missing or vague.
- The roadmap uses a banned vague phrase ("gain experience", "network more", ...).
- `depends_on` points to an unknown step or forms a loop.
- The total hours exceed the hours available before the target date (10% slack).

Going over budget is only a warning.

Text in the gap list is treated as data. The model's tips may not contain links, percentages, or leaked instructions, and `tests/personas/injection.json` tests this.

## Roles

`target_role.role` is one of the nine roles above. If the backend sends only a title, the role is inferred from it, e.g. "Embedded Software Engineer" → Computer Engineer.

- **Project templates** list the `roles` they suit, and the planner never uses an off-role template. A data scientist's "Python" gap won't turn into a security IOC extractor.
- **Resources** may list `roles`. On-role resources are preferred, but off-role ones still match, so shared skills like Docker or SQL work for every role.
- `tests/personas/` has at least one persona per role. The tests check that each role's plans come from the catalog rather than being deferred.

## Levels

`target_role.level` accepts `internship`, `entry`, `mid` or `senior`. Common aliases are also accepted: `intern`, `junior`, `new grad`, `mid-level`.

- **Resources** each have a `level`. When several resources match a gap, the one at the closest level wins.
- **Project templates** list the `levels` they suit. A mid-level engineer won't be told to build a first full-stack app, and an intern won't be handed a design doc.
- Some templates are only for the early levels (hackathon, portfolio project, mock help desk) and some only for mid (mentoring through code reviews, Terraform, observability).

## Serving many users

- The plan is pure computation (no model call), so it handles any number of users.
- Model calls run on `ROADMAP_MODEL_WORKERS` threads (default 1). When every worker is busy, a request gets the basic roadmap immediately instead of waiting in a queue.
- Cache files are keyed by gap list and date, and they contain users' backgrounds. Set `ROADMAP_CACHE_DIR` to private storage in production.
- All options are listed in `.env.example`.

## Adding roles or resources

Coverage is data, not code. To support a new gap, add a resource to `data/catalog.json` or a template to `data/projects.json`:
- Put plain names in `matches`. The longest alias found in the gap text wins.
- Set `level` and `roles` on resources, and `levels` and `roles` on templates.
- Run `pytest`. It checks that every reference and level is valid.

Until the catalog covers a gap, that gap is deferred with a reason rather than dropped.

## Files

```
roadmap/schemas.py      input/output contracts (Pydantic), roles, level aliases, role inference
roadmap/catalog.py      loads the catalog and matches gaps by alias, level and role
roadmap/planner.py      rule-based plan: steps, phases, hours and budget
roadmap/personalize.py  prompt for the local model and per-line tip checks
roadmap/local_model.py  Hugging Face model runner with timeout and worker limit
roadmap/guardrails.py   checks run on every roadmap
roadmap/generate.py     layered entry point
data/catalog.json       118 curated resources across the nine roles
data/projects.json      64 project templates, tagged by level and role
tests/personas/         19 gap lists covering every role across internship, junior and mid
scripts/run_eval.py     live scoreboard for the model's tips (--level, --role)
scripts/save_demo.py    pre-generate demo roadmaps into demo/
```

## Next steps

- Repair retry: send rejected tips back to the model once.
- Career path from incumbent job histories.
- Progress tracking and re-scoring.
- Link checker for the catalog.
- More depth per role: mid-level certs for QA and PM, hardware verification courses.
- Streaming progress in the UI.
