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
ROADMAP_AI=0 .venv/bin/python -m roadmap tests/personas/swe_intern.json --ask   # answer the questions, read the response
.venv/bin/pip install torch transformers            # optional: personal tips
```

## How a response is made

1. **Ask first.** Before planning, the user says how many hours a week they can sustain, when they can start, when they want to be ready, and their budget (`roadmap/intake.py`). Nothing is guessed: without these, `generate_roadmap()` raises `AvailabilityNeeded`.
2. **Plan by priority.** Gaps that most hires have come first, labeled *Must do*, *Should do* and *Nice to have*. Each one becomes a concrete step, labeled by what it earns: a **certification**, a **certificate of completion**, a **portfolio project**, or a **knowledge benefit** when no certificate exists.
3. **Schedule it.** Must-do steps get the user's time first, then should-do, then nice-to-have. If the must-do steps don't all fit, the biggest ones are **shortened** (part 1 on the timeline, part 2 kept as optional), so they stay at the front instead of being dropped. Lower priorities never take time from higher ones. Each step gets start and end dates at the user's pace.
4. **Link the sources.** Every step lists its courses, books and tools with links from the checked catalog.

`roadmap/render.py` turns the result into a readable Markdown response. `roadmap/ui.py` is the Streamlit version: a form for the time questions (dates entered as MM-DD-YYYY), then the timeline, with everything else behind a **Show optional items** button. Try it with:

```bash
.venv/bin/streamlit run scripts/demo_app.py
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

**Budget.** The user chooses what to spend, any amount including $0, or no limit if they leave it blank. The plan stays within it. A certification exam over budget turns into free exam prep on the timeline, with the exam kept as an optional item. Each step can also show **Worth considering** notes, even when they go over budget: a certification for the skill, a free alternative to something paid, or a shorter course.

Everything that isn't on the timeline (over budget, out of time, or a shortened step's part 2) is kept as an `optional` item, which the UI shows behind a **Show optional items** button.

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
- See **Privacy** below for how cached roadmaps are handled.
- All options are listed in `.env.example`.

## Privacy

User information stays private:
- **Nothing leaves the machine.** Planning is local code, and the tip model runs locally. The model is downloaded once; user data is never sent anywhere.
- **No disk storage by default.** Personalized roadmaps are cached in memory only (at most 256, each for 24 hours), keyed by a full SHA-256 hash, so two users can never share an entry. A disk cache is used only if `ROADMAP_CACHE_DIR` is set; its folder and files are readable by the app's own account only, and files are deleted after 24 hours. `generate.clear_cache()` forgets everything right away.
- **No personal text in logs.** Logs record IDs, error types and rejection reasons, never gap text, backgrounds or tips.
- **No usage statistics.** `.streamlit/config.toml` turns off Streamlit's usage statistics. WayPointAI's own app should set the same option.
- The roadmap returned to the UI never includes the user's background text, though personal tips may reflect it.

## Adding roles or resources

Coverage is data, not code. To support a new gap, add a resource to `data/catalog.json` or a template to `data/projects.json`:
- Put plain names in `matches`. The longest alias found in the gap text wins.
- Set `level` and `roles` on resources, and `levels` and `roles` on templates.
- Set `credential` on resources: `certification` (a real exam), `certificate` (only if the provider issues a certificate of completion), or `null`. When unsure, use `null`: the app must never promise a certificate that doesn't exist. The tests check this.
- Run `pytest`. It checks that every reference and level is valid.

Until the catalog covers a gap, that gap is deferred with a reason rather than dropped.

## Files

```
roadmap/schemas.py      input/output contracts (Pydantic), roles, level aliases, role inference
roadmap/intake.py       the availability and workload questions to ask first, and answer parsing
roadmap/render.py       the readable response: priorities, timeline, source links; optional items kept separate
roadmap/ui.py           Streamlit form and roadmap view with the optional-items button
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
scripts/demo_app.py     try the UI with test personas: streamlit run scripts/demo_app.py
scripts/explain.py      print each decision the planner makes for one gap list
```

## Next steps

- Repair retry: send rejected tips back to the model once.
- Career path from incumbent job histories.
- Progress tracking and re-scoring.
- Link checker for the catalog.
- More depth per role: mid-level certs for QA and PM, hardware verification courses.
- Streaming progress in the UI.
